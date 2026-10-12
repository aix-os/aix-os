"""
AIX OS — Faucet (кран).

Раздаёт тестовые AIX указанному адресу, майня специальный блок.
Используется в тестовых сетях, чтобы новые пользователи могли получить монеты.

Запуск:
    python scripts/faucet.py <имя_кошелька_или_адрес> [количество_AIX]

По умолчанию: 100 AIX.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from colorama import Fore, init as colorama_init
import config
from core.chain import Blockchain
from core.block import Block
from core.transaction import Transaction
from core.wallet import Wallet
from storage.db import ChainStorage
from crypto.address import is_valid_address

colorama_init(autoreset=True)


def resolve_address(who: str) -> str:
    if Wallet.exists(who):
        return Wallet.load(who).address
    if is_valid_address(who):
        return who
    raise ValueError(f"'{who}' — не кошелёк и не AIX-адрес")


def main():
    if len(sys.argv) < 2:
        print(f"{Fore.RED}Использование: python scripts/faucet.py <кошелёк_или_адрес> [сумма]")
        return 1

    who = sys.argv[1]
    amount_aix = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0

    try:
        address = resolve_address(who)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}")
        return 1

    storage = ChainStorage(config.CHAIN_DB_PATH)
    chain = storage.load()
    if chain is None:
        chain = Blockchain()
        print(f"{Fore.CYAN}🌱 Создана новая цепочка")

    print(f"{Fore.MAGENTA}{config.ASCII_LOGO}")
    print(f"{Fore.CYAN}🚰 Faucet выдаёт {Fore.YELLOW}{amount_aix} AIX{Fore.CYAN} на адрес:")
    print(f"   {Fore.YELLOW}{address}\n")

    # Faucet-блок: только coinbase с кастомной суммой
    amount_raw = int(amount_aix * config.SATOSHI)
    coinbase = Transaction.create_coinbase(
        recipient=address,
        amount=amount_raw,
        message="AIX OS Faucet — тестовые монеты",
    )

    new_block = Block(
        index=chain.height() + 1,
        timestamp=time.time(),
        transactions=[coinbase],
        previous_hash=chain.last_block().hash,
    )

    print(f"{Fore.CYAN}⛏️  Майню faucet-блок #{new_block.index}...")
    start = time.time()
    attempts = new_block.mine(difficulty=chain.difficulty)
    elapsed = time.time() - start

    ok, msg = chain.add_block(new_block)
    if not ok:
        print(f"{Fore.RED}❌ {msg}")
        return 1

    storage.save(chain)

    balance = chain.get_balance_aix(address)
    print(f"{Fore.GREEN}✅ Готово!")
    print(f"   {Fore.CYAN}Блок:    #{new_block.index}")
    print(f"   {Fore.CYAN}Время:   {elapsed:.2f} сек")
    print(f"   {Fore.CYAN}Hash:    {new_block.hash[:32]}...")
    print(f"   {Fore.CYAN}Баланс:  {Fore.YELLOW}{balance:.4f} AIX")
    return 0


if __name__ == "__main__":
    sys.exit(main())