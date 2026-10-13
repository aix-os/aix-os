"""
AIX OS — патч config.py.

Меняет:
  MAX_SUPPLY / TOTAL_SUPPLY / SUPPLY_MAX → supply
  INITIAL_DIFFICULTY → стартовая сложность
  MIN_DIFFICULTY → минимум
  MAX_DIFFICULTY → максимум (не даёт автоподстройке поднять выше)

Идемпотентен. Бэкап: config.py.cfg.bak

Примеры:
    # Быстрый майнинг: сложность застрянет на 1
    patch_config.py --initial-difficulty 1 --min-difficulty 1 --max-difficulty 1

    # Обычный режим: 5 старт, до 10 максимум
    patch_config.py --initial-difficulty 5 --min-difficulty 1 --max-difficulty 10

    # Смена supply
    patch_config.py --supply 21000000000
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.py"

SUPPLY_NAMES = [
    "MAX_SUPPLY", "TOTAL_SUPPLY", "SUPPLY_MAX",
    "MAX_COINS", "COIN_MAX", "MAX_MONEY",
]


def _patch_int(src: str, name: str, new_val: int) -> tuple[str, bool]:
    """Меняет INT-константу name на new_val."""
    pattern = re.compile(rf"^({name}\s*=\s*)([\d_]+)(.*)$", re.MULTILINE)
    match = pattern.search(src)
    if not match:
        print(f"  [WARN] {name} не найдена")
        return src, False
    current = int(match.group(2).replace("_", ""))
    if current == new_val:
        print(f"  {name} уже {new_val} — пропуск")
        return src, False
    new_src = pattern.sub(
        lambda m: f"{m.group(1)}{new_val}{m.group(3)}",
        src, count=1,
    )
    print(f"  {name}: {current} -> {new_val}")
    return new_src, True


def patch_supply(src: str, new_supply: int) -> tuple[str, bool]:
    for name in SUPPLY_NAMES:
        if re.search(rf"^{name}\s*=", src, re.MULTILINE):
            return _patch_int(src, name, new_supply)
    print(f"  [WARN] Не найдена переменная supply ни из: {SUPPLY_NAMES}")
    return src, False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supply", type=int, default=None)
    parser.add_argument("--initial-difficulty", type=int, default=None)
    parser.add_argument("--min-difficulty", type=int, default=None)
    parser.add_argument("--max-difficulty", type=int, default=None)
    args = parser.parse_args()

    if all(v is None for v in [
        args.supply, args.initial_difficulty,
        args.min_difficulty, args.max_difficulty,
    ]):
        print("Укажи хотя бы один параметр.")
        print("Пример: patch_config.py --initial-difficulty 1 --max-difficulty 1")
        return 1

    if not CONFIG.exists():
        print(f"[FATAL] {CONFIG} не найден")
        return 1

    src = CONFIG.read_text(encoding="utf-8")
    original = src

    print(f"Патчу: {CONFIG.name}")
    print()

    if args.supply is not None:
        src, _ = patch_supply(src, args.supply)

    if args.min_difficulty is not None:
        src, _ = _patch_int(src, "MIN_DIFFICULTY", args.min_difficulty)

    if args.max_difficulty is not None:
        src, _ = _patch_int(src, "MAX_DIFFICULTY", args.max_difficulty)

    if args.initial_difficulty is not None:
        src, _ = _patch_int(src, "INITIAL_DIFFICULTY", args.initial_difficulty)

    if src == original:
        print()
        print("Ничего не изменилось.")
        return 0

    bak = CONFIG.with_suffix(".py.cfg.bak")
    bak.write_bytes(CONFIG.read_bytes())
    print(f"  Бэкап: {bak.name}")

    CONFIG.write_text(src, encoding="utf-8")
    print()
    print("OK.")
    print()
    print("Чтобы применить — сбрось цепочку и перезапусти ноды:")
    print("  .venv\\Scripts\\python.exe scripts\\reset_chain.py")
    print("  .\\scripts\\stop_all.ps1")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())