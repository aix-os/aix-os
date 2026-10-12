"""Отладка AIX Lottery — почему нет побед?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import ChainStorage
from core.protocols.lottery import (
    block_seed, is_lottery_block, LOTTERY_CHANCE,
    pick_lottery_winner,
)

storage = ChainStorage("data/chain_A.json")
bc = storage.load()

print(f"LOTTERY_CHANCE = {LOTTERY_CHANCE}")
print(f"Всего блоков:   {bc.height() + 1}")
print()

# Считаем сколько было бы побед при разных шансах
for chance in (3, 20, 1000):
    wins = sum(1 for b in bc.chain[1:] if block_seed(b) % chance == 0)
    print(f"  Побед при 1/{chance}: {wins} из {bc.height()}")
print()

# Показываем seeds первых 8 блоков
print("Seeds первых 8 блоков:")
for b in bc.chain[1:9]:
    s = block_seed(b)
    print(f"  Блок #{b.index}: seed={s}")
    print(f"    seed % 3    = {s % 3}")
    print(f"    seed % 20   = {s % 20}")
    print(f"    seed % 1000 = {s % 1000}")
    print(f"    is_lottery_block (chance={LOTTERY_CHANCE}) = {is_lottery_block(b)}")
    winner = pick_lottery_winner(bc, b)
    print(f"    winner = {winner[:20] if winner else 'None'}...")
    print()