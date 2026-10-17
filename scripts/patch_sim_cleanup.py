"""
AIX OS — финальная чистка SIM из CLI и доков.

Заменяет в cli/main.py:
  💱 SIM-токены        → 💱 Токены
  💱 SIM-балансы       → 💱 Балансы
  💱 Доступные SIM-токены → 💱 Доступные токены

В docs/WHITEPAPER.md:
  AIX-SIM ↔ USDT-SIM ↔ BTC-SIM → AIX ↔ USDT ↔ BTC
  Любые AIX-SIM / USDT-SIM / BTC-SIM / ETH-SIM / SOL-SIM → без -SIM

Идемпотентен. Бэкапы: main.py.sim.bak, WHITEPAPER.md.sim.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_sim_cleanup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLI = ROOT / "cli" / "main.py"
WHP = ROOT / "docs" / "WHITEPAPER.md"


# Пары замена для CLI (порядок важен — длинные раньше)
CLI_REPLACEMENTS = [
    ("💱 Доступные SIM-токены", "💱 Доступные токены"),
    ("💱 SIM-балансы", "💱 Балансы"),
    ("💱 SIM-токены", "💱 Токены"),
    ("SIM-токенов", "токенов"),
    ("SIM-балансы", "Балансы"),
]


# Пары замена для WHITEPAPER (порядок важен)
WHP_REPLACEMENTS = [
    ("AIX-SIM ↔ USDT-SIM ↔ BTC-SIM", "AIX ↔ USDT ↔ BTC"),
    ("AIX-SIM", "AIX"),
    ("USDT-SIM", "USDT"),
    ("USDC-SIM", "USDC"),
    ("BTC-SIM", "BTC"),
    ("ETH-SIM", "ETH"),
    ("SOL-SIM", "SOL"),
    ("TON-SIM", "TON"),
    ("BNB-SIM", "BNB"),
    ("XRP-SIM", "XRP"),
    ("ADA-SIM", "ADA"),
    ("DOGE-SIM", "DOGE"),
    ("DOT-SIM", "DOT"),
    ("MATIC-SIM", "MATIC"),
    ("AVAX-SIM", "AVAX"),
    ("LTC-SIM", "LTC"),
    ("TRX-SIM", "TRX"),
    ("LINK-SIM", "LINK"),
    ("ATOM-SIM", "ATOM"),
    ("UNI-SIM", "UNI"),
    ("XMR-SIM", "XMR"),
]


def patch_file(path: Path, replacements: list, backup_suffix: str) -> bool:
    if not path.exists():
        print(f"[SKIP] {path.relative_to(ROOT)} — нет файла")
        return False

    src = path.read_text(encoding="utf-8")
    original = src

    applied = []
    for old, new in replacements:
        n = src.count(old)
        if n > 0:
            src = src.replace(old, new)
            applied.append((old, new, n))

    if src == original:
        print(f"[SKIP] {path.relative_to(ROOT)} — нечего менять")
        return False

    bak = path.with_suffix(path.suffix + backup_suffix)
    bak.write_bytes(path.read_bytes())

    path.write_text(src, encoding="utf-8")

    print(f"[{path.relative_to(ROOT)}] OK:")
    for old, new, n in applied:
        print(f"   '{old}' -> '{new}'  ({n} замен)")
    print(f"   Бэкап: {bak.name}")
    return True


def main() -> int:
    print("Чищу SIM из CLI и WHITEPAPER...")
    print()

    changed = 0
    if patch_file(CLI, CLI_REPLACEMENTS, ".sim.bak"):
        changed += 1
    if patch_file(WHP, WHP_REPLACEMENTS, ".sim.bak"):
        changed += 1

    print()
    if changed == 0:
        print("Нечего менять — всё уже чисто.")
        return 0

    print(f"Готово. Файлов изменено: {changed}.")
    print()
    print("Проверь остатки вручную:")
    print("   Select-String -Path cli\\main.py,docs\\WHITEPAPER.md "
          "-Pattern 'SIM'")
    return 0


if __name__ == "__main__":
    sys.exit(main())