"""
Патч network/server.py — добавляет Faucet в ноду.

Что добавляет:
- импорт FaucetManager
- создание faucet_manager в create_app
- эндпоинты:
    GET  /faucet/stats        — сводка
    POST /faucet/claim        — выдать AIX на адрес
    GET  /faucet/log?limit=N  — журнал выдач

Идемпотентен. Бэкап: server.py.faucet.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_faucet_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"

MARKER = "/faucet/claim"


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:120]!r}"
        )
    return src.replace(anchor, replacement, 1)


# ---------- 1. Импорт ----------

IMPORT_ANCHOR = "from core.governance.dao import DAOManager"
IMPORT_ADD = "\nfrom core.protocols.faucet import FaucetManager"


# ---------- 2. Pydantic-модель ----------

MODEL_ANCHOR = "class DAOCancelRequest(BaseModel):\n    by: str"
MODEL_ADD = (
    "\n\n\nclass FaucetClaimRequest(BaseModel):\n"
    "    address: str"
)


# ---------- 3. Создание faucet_manager + sender/loader ----------

INIT_ANCHOR = (
    "    dao_manager = DAOManager(dao_path, blockchain=blockchain, "
    "sbt_manager=sbt_manager, poc_manager=poc_manager)"
)
INIT_ADD = '''

    faucet_path = Path(data_file).parent / f"faucet_{port}.json"
    faucet_manager = FaucetManager(faucet_path, blockchain=blockchain)

    # ---- Faucet helpers ----

    def _faucet_wallet_loader(name: str):
        """Загрузить кошелёк-казначей."""
        return Wallet.load(name)

    def _faucet_send(sender_addr: str, recipient: str,
                     amount_aix: float, private_key_hex: str) -> str:
        """Отправить AIX от казначея получателю. Возвращает tx_id."""
        from crypto.keys import private_key_from_bytes
        amount_raw = int(amount_aix * config.SATOSHI)
        tx = Transaction(
            sender=sender_addr,
            recipient=recipient,
            amount=amount_raw,
            fee=0,
            message="AIX faucet",
        )
        sk = private_key_from_bytes(bytes.fromhex(private_key_hex))
        tx.sign_transaction(sk)
        ok, msg = tx.is_valid()
        if not ok:
            raise ValueError(msg)
        ok, msg = blockchain.mempool.add(tx)
        if not ok:
            raise ValueError(msg)
        storage.save(blockchain)
        peer_manager.broadcast_transaction(tx.to_dict())
        return tx.tx_id()
'''


# ---------- 4. Эндпоинты перед P2P ----------

P2P_ANCHOR = (
    '    # =========================================================================\n'
    '    # P2P\n'
    '    # =========================================================================\n'
    '\n'
    '    @app.get("/peers")'
)

FAUCET_BLOCK = '''    # =========================================================================
    # FAUCET
    # =========================================================================

    @app.get("/faucet/stats")
    def faucet_stats():
        return faucet_manager.stats()

    @app.get("/faucet/log")
    def faucet_log(limit: int = 50):
        return {
            "count": faucet_manager.count(),
            "entries": faucet_manager.log(limit=limit),
        }

    @app.post("/faucet/claim")
    def faucet_claim(req: FaucetClaimRequest, request: Request):
        # Определяем IP: прямой или через X-Forwarded-For (туннель)
        ip = "?"
        if request.client and request.client.host:
            ip = request.client.host
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            ip = xff.split(",")[0].strip()

        ok, result = faucet_manager.claim(
            address=req.address,
            ip=ip,
            wallet_loader=_faucet_wallet_loader,
            sender=_faucet_send,
        )
        if not ok:
            raise HTTPException(400, result.get("error", "не удалось"))
        return result

'''


def main() -> int:
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1

    src = SERVER.read_text(encoding="utf-8")

    if MARKER in src:
        print("[server.py] уже пропатчен — пропуск")
        return 0

    # Проверим, что Request импортируется
    if "from fastapi import" not in src:
        print("[FATAL] Не найден импорт fastapi")
        return 1

    bak = SERVER.with_suffix(SERVER.suffix + ".faucet.bak")
    bak.write_bytes(SERVER.read_bytes())
    print(f"[server.py] backup -> {bak.name}")

    src = _replace_once(src, IMPORT_ANCHOR,
                        IMPORT_ANCHOR + IMPORT_ADD,
                        "import")
    src = _replace_once(src, MODEL_ANCHOR,
                        MODEL_ANCHOR + MODEL_ADD,
                        "pydantic model")
    src = _replace_once(src, INIT_ANCHOR,
                        INIT_ANCHOR + INIT_ADD,
                        "create_app init")
    src = _replace_once(src, P2P_ANCHOR,
                        FAUCET_BLOCK + P2P_ANCHOR,
                        "P2P anchor")

    # Проверим, что Request импортируется из fastapi, если нет — добавим
    if "Request" not in src.split("\n")[15]:
        # Простая проверка — если в первой части файла нет Request в импорте
        head = "\n".join(src.split("\n")[:50])
        if "from fastapi import" in head and " Request" not in head and ",Request" not in head:
            # Заменим первую строку fastapi-импорта
            for line in src.split("\n"):
                if line.startswith("from fastapi import"):
                    new_line = line.replace(
                        "from fastapi import",
                        "from fastapi import Request, ",
                        1,
                    ).replace("Request, ,", "Request, ")
                    src = src.replace(line, new_line, 1)
                    print("  добавлен Request в импорт fastapi")
                    break

    SERVER.write_text(src, encoding="utf-8")
    print("[server.py] OK: /faucet/stats, /faucet/claim, /faucet/log добавлены")
    print()
    print("Готово. Дальше:")
    print("  1) Перезапусти ноды:  .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")
    print("  2) Назначь казначея:  файл 4 (faucet_setup.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())