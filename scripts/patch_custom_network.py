"""
AIX OS — патч Custom Network.

Добавляет в config.py:
  CHAIN_ID = 21069
  NETWORK_NAME = "AIX OS"
  NETWORK_SYMBOL = "AIX"
  NETWORK_DECIMALS = 18

Добавляет в network/server.py:
  GET  /network/config      — JSON для «Add Network» в MetaMask
  POST /rpc                 — JSON-RPC, отвечает на eth_* методы MetaMask

Идемпотентен. Бэкапы: config.py.cn.bak, server.py.cn.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_custom_network.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.py"
SERVER = ROOT / "network" / "server.py"

MARKER = "# CUSTOM-NETWORK"


def _patch_config() -> bool:
    print(f"\n[config.py] {CONFIG}")
    src = CONFIG.read_text(encoding="utf-8")

    if MARKER in src or "CHAIN_ID = 21069" in src:
        print("  уже пропатчен — пропуск")
        return False

    bak = CONFIG.with_suffix(".py.cn.bak")
    bak.write_bytes(CONFIG.read_bytes())
    print(f"  backup -> {bak.name}")

    block = """

# CUSTOM-NETWORK: параметры для MetaMask / Trust Wallet
CHAIN_ID = 21069          # уникальный ID, не занят в chainlist.org
NETWORK_NAME = "AIX OS"
NETWORK_SYMBOL = "AIX"
NETWORK_DECIMALS = 18

"""

    # Вставляем перед последней строкой-комментарием "# ====" или в конец файла
    src = src.rstrip() + "\n" + block
    CONFIG.write_text(src, encoding="utf-8")
    print("  OK: CHAIN_ID, NETWORK_NAME, NETWORK_SYMBOL добавлены")
    return True


def _patch_server() -> bool:
    print(f"\n[server.py] {SERVER}")
    src = SERVER.read_text(encoding="utf-8")

    if MARKER in src or "/network/config" in src:
        print("  уже пропатчен — пропуск")
        return False

    anchor = (
        '    # =========================================================================\n'
        '    # P2P\n'
        '    # =========================================================================\n'
        '\n'
        '    @app.get("/peers")'
    )

    if anchor not in src:
        print("[FATAL] Не найден якорь P2P.")
        print("  Скинь мне network/server.py — пересчитаю.")
        return False

    bak = SERVER.with_suffix(".py.cn.bak")
    bak.write_bytes(SERVER.read_bytes())
    print(f"  backup -> {bak.name}")

    custom_block = '''    # =========================================================================
    # CUSTOM-NETWORK: MetaMask / Trust Wallet
    # =========================================================================

    @app.get("/network/config")
    def network_config():
        """JSON для кнопки «Add Network» в MetaMask."""
        return {
            "chainId": hex(config.CHAIN_ID),
            "chainName": config.NETWORK_NAME,
            "nativeCurrency": {
                "name": config.NETWORK_SYMBOL,
                "symbol": config.NETWORK_SYMBOL,
                "decimals": config.NETWORK_DECIMALS,
            },
            "rpcUrls": [f"{self_url}/rpc"],
            "blockExplorerUrls": [],
        }

    @app.post("/rpc")
    def rpc_handler(req: dict):
        """
        Минимальный Ethereum JSON-RPC — для MetaMask/Trust.
        Поддерживает: eth_chainId, net_version, eth_blockNumber,
        eth_getBalance, eth_accounts, eth_gasPrice, eth_syncing,
        web3_clientVersion, eth_call (заглушка), eth_estimateGas.
        """
        method = req.get("method", "")
        params = req.get("params", [])
        req_id = req.get("id", 1)

        def _ok(result):
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        def _err(code, msg):
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": code, "message": msg}}

        if method == "eth_chainId":
            return _ok(hex(config.CHAIN_ID))

        if method == "net_version":
            return _ok(str(config.CHAIN_ID))

        if method == "web3_clientVersion":
            return _ok(f"AIX-OS/v{config.VERSION}")

        if method == "eth_blockNumber":
            return _ok(hex(blockchain.height()))

        if method == "eth_syncing":
            return _ok(False)

        if method == "eth_gasPrice":
            return _ok("0x0")

        if method == "eth_accounts":
            return _ok([])

        if method == "eth_getBalance":
            try:
                addr = params[0] if params else ""
                # MetaMask отправляет 0x-адреса, но у нас AIX-адреса.
                # Возвращаем 0, если не можем сопоставить.
                bal = 0
                if addr and addr.startswith("AIX"):
                    bal = blockchain.get_balance(addr)
                return _ok(hex(bal))
            except Exception:
                return _ok("0x0")

        if method == "eth_call":
            # Заглушка — MetaMask вызывает для проверки контрактов
            return _ok("0x")

        if method == "eth_estimateGas":
            return _ok("0x5208")  # 21000 в hex

        # Всё остальное — ошибка method not found
        return _err(-32601, f"Method not found: {method}")

'''

    src = src.replace(anchor, custom_block + anchor, 1)
    SERVER.write_text(src, encoding="utf-8")
    print("  OK: /network/config и /rpc добавлены")
    return True


def main() -> int:
    if not CONFIG.exists():
        print(f"[FATAL] {CONFIG} не найден")
        return 1
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1

    config_changed = _patch_config()
    server_changed = _patch_server()

    if not config_changed and not server_changed:
        print("\nВсё уже пропатчено.")
        return 0

    print()
    print("OK. Перезапусти ноды:")
    print("  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force")
    print("  .\\scripts\\run_all.ps1")
    print()
    print("Проверка после перезапуска:")
    print("  Invoke-RestMethod http://127.0.0.1:8010/network/config")
    return 0


if __name__ == "__main__":
    sys.exit(main())