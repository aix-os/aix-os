"""
Патч network/server.py — эндпоинт POST /tx/submit.

Принимает УЖЕ ПОДПИСАННУЮ транзакцию (без private_key).
Проверяет подпись через Transaction.is_valid().
Кладёт в mempool, рассылает пирам.

Это «правильный» путь: приватный ключ никогда не уходит с устройства.

Идемпотентен. Бэкап: server.py.txsubmit.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_tx_submit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"

MARKER = "/tx/submit"


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:120]!r}"
        )
    return src.replace(anchor, replacement, 1)


# ---------- 1. Pydantic-модель ----------

MODEL_ANCHOR = "class CreatePublicWalletRequest(BaseModel):\n    name: str | None = None"

MODEL_ADD = '''


class SubmitTxRequest(BaseModel):
    sender: str
    recipient: str
    amount: int
    timestamp: float
    fee: int = 0
    message: str = ""
    public_key: str
    signature: str'''

MODEL_ANCHOR_ALT = "class SyncStateEventRequest(BaseModel):\n    event: dict\n    from_peer: str = \"\""

# ---------- 2. Эндпоинт — перед P2P ----------

P2P_ANCHOR = (
    '    # =========================================================================\n'
    '    # P2P\n'
    '    # =========================================================================\n'
    '\n'
    '    @app.get("/peers")'
)

ENDPOINT_BLOCK = '''    # =========================================================================
    # TRANSACTION SUBMIT (подписанная транзакция от кошелька)
    # =========================================================================

    @app.post("/tx/submit")
    def tx_submit(req: SubmitTxRequest):
        """
        Принять подписанную транзакцию от кошелька (мобильного/десктопного).
        Приватный ключ НЕ передаётся — только подпись и публичный ключ.
        """
        tx = Transaction(
            sender=req.sender,
            recipient=req.recipient,
            amount=req.amount,
            timestamp=req.timestamp,
            fee=req.fee,
            message=req.message,
            public_key=req.public_key,
            signature=req.signature,
        )

        ok, msg = tx.is_valid()
        if not ok:
            raise HTTPException(400, f"Транзакция невалидна: {msg}")

        # Проверка баланса для обычных отправителей
        if tx.sender not in ("COINBASE", "LOTTERY", "POC-POOL"):
            balance = blockchain.get_balance(tx.sender)
            locked = total_locked(tx.sender)
            available = balance - locked
            if available < tx.amount + tx.fee:
                raise HTTPException(
                    400,
                    f"Недостаточно средств: доступно "
                    f"{available / config.SATOSHI:.4f} AIX"
                )

        ok, msg = blockchain.mempool.add(tx)
        if not ok:
            raise HTTPException(400, msg)

        storage.save(blockchain)
        broadcast_count = peer_manager.broadcast_transaction(tx.to_dict())

        return {
            "status": "accepted",
            "tx_id": tx.tx_id(),
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "mempool_size": blockchain.mempool.size(),
            "broadcast_to_peers": broadcast_count,
        }

'''


def main() -> int:
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1

    src = SERVER.read_text(encoding="utf-8")

    if MARKER in src:
        print("[server.py] уже пропатчен — пропуск")
        return 0

    bak = SERVER.with_suffix(SERVER.suffix + ".txsubmit.bak")
    bak.write_bytes(SERVER.read_bytes())
    print(f"[server.py] backup -> {bak.name}")

    # Модель
    if MODEL_ANCHOR in src:
        src = _replace_once(src, MODEL_ANCHOR,
                            MODEL_ANCHOR + MODEL_ADD,
                            "pydantic model (CreatePublicWalletRequest)")
    elif MODEL_ANCHOR_ALT in src:
        src = _replace_once(src, MODEL_ANCHOR_ALT,
                            MODEL_ANCHOR_ALT + MODEL_ADD,
                            "pydantic model (SyncStateEventRequest)")
    else:
        print("[FATAL] Не найден якорь для Pydantic-модели.")
        print("  Искал: CreatePublicWalletRequest или SyncStateEventRequest")
        return 1

    # Эндпоинт
    src = _replace_once(src, P2P_ANCHOR,
                        ENDPOINT_BLOCK + P2P_ANCHOR,
                        "P2P anchor")

    SERVER.write_text(src, encoding="utf-8")
    print("[server.py] OK: /tx/submit добавлен")
    print()
    print("Перезапусти ноды:")
    print("  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())