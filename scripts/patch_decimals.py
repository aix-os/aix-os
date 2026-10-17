"""
AIX OS — переход с DECIMALS=18 на DECIMALS=8.

Зачем: Dart int — 64 бита. Максимум 9.2 × 10^18. При 1 AIX = 10^18
сатоши, 50 AIX = 5 × 10^19 — не влезает в int64.

Решение: DECIMALS=8 (как в Bitcoin).
1 AIX = 10^8 = 100 000 000 сатоши.
21 млрд AIX = 2.1 × 10^18 — влезает с запасом.

Что делает скрипт:
1. config.py: DECIMALS 18 → 8
2. Меняет ВСЕ хардкодные 10**18 / 10 ** 18 на config.SATOSHI
   в ключевых файлах (swap.py, server.py, cli/main.py, setup_swap_pools.py)
3. В тестовых литералах (block.py, mempool.py, poc.py) — заменяет на 10**8

Бэкап: *.dec.bak рядом с оригиналом.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_decimals.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG = ROOT / "config.py"

# Файлы, где 10**18 меняем на config.SATOSHI (там есть импорт config)
USE_CONFIG_FILES = [
    ROOT / "core" / "protocols" / "swap.py",
    ROOT / "network" / "server.py",
    ROOT / "cli" / "main.py",
    ROOT / "scripts" / "setup_swap_pools.py",
]

# Файлы, где 10**18 меняем просто на 10**8 (тесты, нет config)
USE_NEW_LITERAL_FILES = [
    ROOT / "core" / "block.py",
    ROOT / "core" / "mempool.py",
    ROOT / "core" / "protocols" / "poc.py",
]


def _backup(p: Path) -> None:
    b = p.with_suffix(p.suffix + ".dec.bak")
    if not b.exists():
        b.write_bytes(p.read_bytes())


def patch_config() -> bool:
    print(f"[config.py]")
    if not CONFIG.exists():
        print(f"  [FATAL] {CONFIG} не найден")
        return False

    src = CONFIG.read_text(encoding="utf-8")
    _backup(CONFIG)

    # DECIMALS = 18 → 8
    pattern = re.compile(r"^(DECIMALS\s*=\s*)(\d+)(.*)$", re.MULTILINE)
    match = pattern.search(src)
    if not match:
        print("  [WARN] Не найдена DECIMALS")
        return False

    current = int(match.group(2))
    if current == 8:
        print("  DECIMALS уже 8 — пропуск")
    else:
        src = pattern.sub(
            lambda m: f"{m.group(1)}8{m.group(3)}",
            src, count=1,
        )
        print(f"  DECIMALS: {current} -> 8")
        CONFIG.write_text(src, encoding="utf-8")

    return True


def patch_file_use_config(p: Path) -> int:
    """Заменяет 10**18 → config.SATOSHI в файлах, где есть import config."""
    if not p.exists():
        print(f"  [SKIP] {p.name} — нет файла")
        return 0

    src = p.read_text(encoding="utf-8")
    _backup(p)

    # Регекс: "10**18" или "10 ** 18" с опциональными пробелами
    pattern = re.compile(r"10\s*\*\*\s*18")
    n = len(pattern.findall(src))

    if n == 0:
        print(f"  [{p.name}] нет 10**18 — пропуск")
        return 0

    new_src = pattern.sub("config.SATOSHI", src)
    p.write_text(new_src, encoding="utf-8")
    print(f"  [{p.name}] заменено {n} вхождений -> config.SATOSHI")
    return n


def patch_file_new_literal(p: Path) -> int:
    """Заменяет 10**18 → 10**8 в файлах без config."""
    if not p.exists():
        print(f"  [SKIP] {p.name} — нет файла")
        return 0

    src = p.read_text(encoding="utf-8")
    _backup(p)

    pattern = re.compile(r"10\s*\*\*\s*18")
    n = len(pattern.findall(src))

    if n == 0:
        print(f"  [{p.name}] нет 10**18 — пропуск")
        return 0

    new_src = pattern.sub("10**8", src)
    p.write_text(new_src, encoding="utf-8")
    print(f"  [{p.name}] заменено {n} вхождений -> 10**8")
    return n


def main() -> int:
    print("=" * 60)
    print("  Переход AIX OS на DECIMALS=8")
    print("=" * 60)
    print()

    total = 0

    print("1. Конфиг")
    if patch_config():
        total += 1
    print()

    print("2. Замена 10**18 -> config.SATOSHI")
    for p in USE_CONFIG_FILES:
        total += patch_file_use_config(p)
    print()

    print("3. Замена 10**18 -> 10**8 (тестовые файлы)")
    for p in USE_NEW_LITERAL_FILES:
        total += patch_file_new_literal(p)
    print()

    print("=" * 60)
    print(f"  Готово. Всего заменено: {total}")
    print("=" * 60)
    print()
    print("Дальше по шагам:")
    print("  1. Сбросить цепочку:  .venv\\Scripts\\python.exe scripts\\reset_chain.py")
    print("  2. Обновить swap-пулы: .venv\\Scripts\\python.exe scripts\\setup_swap_pools.py")
    print("  3. Создать кошельки:   .venv\\Scripts\\python.exe scripts\\setup_founder_wallets.py")
    print("  4. Перезапустить ноды: .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")
    print("  5. Намайнить:          .venv\\Scripts\\python.exe scripts\\mine_founder.py --wallet founder")
    return 0


if __name__ == "__main__":
    sys.exit(main())