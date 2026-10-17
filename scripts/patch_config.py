"""
AIX OS — патч config.py.

Меняет:
  MAX_SUPPLY / TOTAL_SUPPLY / SUPPLY_MAX → supply
  INITIAL_DIFFICULTY → стартовая сложность
  MIN_DIFFICULTY → минимум
  MAX_DIFFICULTY → максимум
  MINE_SAVE_EVERY_N_BLOCKS → как часто сохранять chain при майнинге
  MINE_BROADCAST → рассылать ли блок пирам

Идемпотентен. Бэкап: config.py.cfg.bak

Примеры:
    # Быстрый майнинг:
    patch_config.py --initial-difficulty 1 --min-difficulty 1 --max-difficulty 1
    patch_config.py --mine-save-every 100 --mine-broadcast off

    # Обычный режим после майнинга:
    patch_config.py --initial-difficulty 5 --min-difficulty 1 --max-difficulty 10
    patch_config.py --mine-save-every 1 --mine-broadcast on

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


def _patch_bool(src: str, name: str, new_val: bool) -> tuple[str, bool]:
    """Меняет BOOL-константу name на new_val (True/False)."""
    pattern = re.compile(rf"^({name}\s*=\s*)(True|False)(.*)$", re.MULTILINE)
    match = pattern.search(src)
    if not match:
        print(f"  [WARN] {name} не найдена")
        return src, False
    current = match.group(2) == "True"
    if current == new_val:
        print(f"  {name} уже {new_val} — пропуск")
        return src, False
    val_str = "True" if new_val else "False"
    new_src = pattern.sub(
        lambda m: f"{m.group(1)}{val_str}{m.group(3)}",
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
    parser.add_argument("--mine-save-every", type=int, default=None,
                        help="Как часто сохранять chain (1 = каждый блок)")
    parser.add_argument("--mine-broadcast", choices=["on", "off"], default=None,
                        help="on / off — рассылать блок пирам")
    args = parser.parse_args()

    if all(v is None for v in [
        args.supply, args.initial_difficulty, args.min_difficulty,
        args.max_difficulty, args.mine_save_every, args.mine_broadcast,
    ]):
        print("Укажи хотя бы один параметр.")
        print(__doc__)
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

    if args.mine_save_every is not None:
        src, _ = _patch_int(src, "MINE_SAVE_EVERY_N_BLOCKS", args.mine_save_every)

    if args.mine_broadcast is not None:
        src, _ = _patch_bool(src, "MINE_BROADCAST", args.mine_broadcast == "on")

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
    print("Перезапусти ноды для применения:")
    print("  .\\scripts\\stop_all.ps1")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())