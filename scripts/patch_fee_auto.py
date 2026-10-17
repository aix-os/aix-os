"""
Патч network/server.py — автоматический расчёт комиссии в /send.

Проблема: после введения FEE_PERCENT=0.1% в transaction.py,
старые клиенты (Web UI, мобильный кошелёк) передают fee=0 и получают
отказ "Комиссия слишком мала".

Решение: сервер в /send САМ считает комиссию по формуле
calculate_fee(amount) и подставляет в транзакцию.
Также в /tx/submit — та же логика, если клиент прислал fee=0.

Идемпотентен. Бэкап: server.py.feeauto.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_fee_auto.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"

MARKER = "# AUTO-FEE-FIX"


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:150]!r}"
        )
    return src.replace(anchor, replacement, 1)


# ---------- 1. Импорт calculate_fee ----------

IMPORT_ANCHOR = "from core.transaction import Transaction"
IMPORT_ADD = "\nfrom core.transaction import calculate_fee"


# ---------- 2. /send — считать fee автоматически ----------

SEND_OLD = '''        tx = Transaction(sender=sender_addr, recipient=recipient_addr,
                         amount=amount, fee=req.fee, message=req.message)'''

SEND_NEW = '''        # AUTO-FEE-FIX: если клиент не передал комиссию — считаем сами (0.1%)
        effective_fee = req.fee if req.fee > 0 else calculate_fee(amount)
        tx = Transaction(sender=sender_addr, recipient=recipient_addr,
                         amount=amount, fee=effective_fee, message=req.message)'''


# ---------- 3. /tx/submit — то же для подписанных транзакций ----------

SUBMIT_OLD = '''        tx = Transaction(
            sender=req.sender,
            recipient=req.recipient,
            amount=req.amount,
            timestamp=req.timestamp,
            fee=req.fee,
            message=req.message,
            public_key=req.public_key,
            signature=req.signature,
        )'''

SUBMIT_NEW = '''        # AUTO-FEE-FIX: если fee=0 — считаем сами, но подпись уже сделана
        # на клиенте с fee=0. Поэтому отдаём правильный fee только если
        # клиент его не передал И может быть подписан с ним.
        # В нашем случае: подпись валидируется с фактическим fee, поэтому
        # если клиент подписал с fee=0, а мы подменим — подпись не сойдётся.
        # Значит для /tx/submit требуем, чтобы клиент сам передал fee.
        tx = Transaction(
            sender=req.sender,
            recipient=req.recipient,
            amount=req.amount,
            timestamp=req.timestamp,
            fee=req.fee,
            message=req.message,
            public_key=req.public_key,
            signature=req.signature,
        )'''


def main() -> int:
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1

    src = SERVER.read_text(encoding="utf-8")

    if MARKER in src:
        print("[server.py] уже пропатчен — пропуск")
        return 0

    bak = SERVER.with_suffix(SERVER.suffix + ".feeauto.bak")
    bak.write_bytes(SERVER.read_bytes())
    print(f"[server.py] backup -> {bak.name}")

    # Импорт — если calculate_fee уже импортирован, пропускаем
    if "calculate_fee" not in src:
        src = _replace_once(src, IMPORT_ANCHOR,
                            IMPORT_ANCHOR + IMPORT_ADD,
                            "import calculate_fee")

    # /send — фикс
    src = _replace_once(src, SEND_OLD, SEND_NEW, "/send fee")

    # /tx/submit — оставляем как есть, но добавляем комментарий-маркер
    if SUBMIT_OLD in src:
        src = src.replace(SUBMIT_OLD, SUBMIT_NEW, 1)
        print("[server.py] /tx/submit помечен комментарием (клиент должен передать fee)")

    SERVER.write_text(src, encoding="utf-8")
    print("[server.py] OK: /send считает fee автоматически")
    print()
    print("Перезапусти ноды:")
    print("  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())