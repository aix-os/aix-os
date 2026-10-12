"""
AIX OS — Сброс данных.

Удаляет:
- data/chain.json (вся цепочка)
- data/wallets/*.wallet.json (все кошельки) — опционально
- data/*.tmp (временные файлы)

Запуск:
    python scripts/reset_db.py           # сбросить только цепочку
    python scripts/reset_db.py --all     # сбросить и кошельки тоже
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import Fore, init as colorama_init
import config

colorama_init(autoreset=True)


def main():
    reset_all = "--all" in sys.argv

    print(f"{Fore.MAGENTA}{config.ASCII_LOGO}")
    print(f"{Fore.YELLOW}⚠️  СБРОС ДАННЫХ AIX OS\n")

    deleted = []

    # Цепочка
    if config.CHAIN_DB_PATH.exists():
        config.CHAIN_DB_PATH.unlink()
        deleted.append(f"Цепочка: {config.CHAIN_DB_PATH}")
        print(f"{Fore.GREEN}🗑️  Удалена цепочка")
    else:
        print(f"{Fore.CYAN}ℹ️  Цепочка не найдена")

    # Временные файлы
    for tmp in config.DATA_DIR.glob("*.tmp"):
        tmp.unlink()
        deleted.append(f"Временный: {tmp}")

    # Кошельки
    if reset_all:
        wallets = list(config.WALLETS_DIR.glob("*.wallet.json"))
        for w in wallets:
            w.unlink()
            deleted.append(f"Кошелёк: {w.name}")
        print(f"{Fore.GREEN}🗑️  Удалено кошельков: {len(wallets)}")

    print()
    if deleted:
        print(f"{Fore.GREEN}✅ Сброшено объектов: {len(deleted)}")
    else:
        print(f"{Fore.YELLOW}Нечего удалять")
    print()
    print(f"{Fore.CYAN}Теперь можно начать заново:")
    print(f"   python scripts/init_genesis.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())