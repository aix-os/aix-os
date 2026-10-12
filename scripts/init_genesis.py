"""
AIX OS — Инициализация генезис-блока.

Создаёт цепочку с нуля и показывает сводку.
Запуск:
    python scripts/init_genesis.py

⚠️  ВНИМАНИЕ: удалит текущую цепочку, если она существует!
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import Fore, init as colorama_init
import config
from core.chain import Blockchain
from storage.db import ChainStorage

colorama_init(autoreset=True)


def main():
    print(f"{Fore.MAGENTA}{config.ASCII_LOGO}")

    storage = ChainStorage(config.CHAIN_DB_PATH)

    if storage.exists():
        print(f"{Fore.YELLOW}⚠️  Цепочка уже существует: {config.CHAIN_DB_PATH}")
        answer = input(f"{Fore.YELLOW}Удалить и создать новую? (yes/no): ").strip().lower()
        if answer != "yes":
            print(f"{Fore.RED}❌ Отменено")
            return 1
        storage.delete()
        print(f"{Fore.CYAN}🗑️  Старая цепочка удалена")

    print(f"{Fore.CYAN}🌱 Создаю генезис-блок...")
    chain = Blockchain()
    storage.save(chain)

    genesis = chain.chain[0]
    print(f"{Fore.GREEN}✅ Генезис создан!\n")
    print(f"   {Fore.CYAN}Высота:     {Fore.YELLOW}{chain.height()}")
    print(f"   {Fore.CYAN}Hash:       {Fore.YELLOW}{genesis.hash}")
    print(f"   {Fore.CYAN}Timestamp:  {Fore.YELLOW}{genesis.timestamp}")
    print(f"   {Fore.CYAN}Сообщение:  {Fore.YELLOW}{config.GENESIS_MESSAGE}")
    print()
    print(f"{Fore.CYAN}📂 Данные: {config.DATA_DIR}")
    print(f"{Fore.GREEN}🚀 AIX OS готов к работе! Создай кошелёк: python cli/main.py wallet new alice")
    return 0


if __name__ == "__main__":
    sys.exit(main())