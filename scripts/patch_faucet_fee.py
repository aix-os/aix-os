"""
Патч network/server.py — комиссия в _faucet_send.

Проблема: faucet создаёт Transaction с fee=0, а transaction.py требует 0.1%.
Решение: считаем fee автоматически через calculate_fee.

Идемпотентен. Бэкап: server.py.faucetfee.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_faucet_fee.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"

MARKER = "# FAUCET-FEE-FIX"


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:150]!r}"
        )
    return src.replace(anchor, replacement, 1)


# Ищем создание Transaction внутри _faucet_send
OLD = '''        amount_raw = int(amount_aix * config.SATOSHI)
        tx = Transaction(
            sender=sender_addr,
            recipient=recipient,
            amount=amount_raw,
            fee=0,
            message="AIX faucet",
        )'''

NEW = '''        amount_raw = int(amount_aix * config.SATOSHI)
        # FAUCET-FEE-FIX: считаем комиссию 0.1%, чтобы прошло is_valid()
        from core.transaction import calculate_fee
        fee_raw = calculate_fee(amount_raw)
        tx = Transaction(
            sender=sender_addr,
            recipient=recipient,
            amount=amount_raw,
            fee=fee_raw,
            message="AIX faucet",
        )'''


def main() -> int:
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1

    src = SERVER.read_text(encoding="utf-8")

    if MARKER in src:
        print("[server.py] уже пропатчен — пропуск")
        return 0

    if OLD not in src:
        print("[FATAL] Не найден якорь _faucet_send Transaction.")
        print("  Искал создание tx с fee=0 в контексте faucet.")
        print("  Скинь мне network/server.py — найду вручную.")
        return 1

    bak = SERVER.with_suffix(SERVER.suffix + ".faucetfee.bak")
    bak.write_bytes(SERVER.read_bytes())
    print(f"[server.py] backup -> {bak.name}")

    src = _replace_once(src, OLD, NEW, "_faucet_send fee")
    SERVER.write_text(src, encoding="utf-8")

    print("[server.py] OK: faucet теперь считает комиссию 0.1%")
    print()
    print("Перезапусти ноды:")
    print("  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())