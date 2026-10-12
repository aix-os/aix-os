"""
AIX OS — Блокчейн (цепочка блоков).

Особенность: транзакции с recipient="BURN" уменьшают supply (сжигание).
"""

import time
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.block import Block
from core.transaction import Transaction
from core.mempool import Mempool

import config


class Blockchain:
    """Цепочка блоков AIX."""

    def __init__(self):
        self.chain: list = []
        self.mempool = Mempool()
        self.difficulty: int = config.INITIAL_DIFFICULTY
        self._create_genesis()

    def _create_genesis(self) -> None:
        genesis = Block.create_genesis(config.GENESIS_MESSAGE)
        self.chain.append(genesis)

    def add_block(self, block: Block) -> tuple:
        previous_block = self.last_block()
        ok, msg = block.is_valid(previous_block=previous_block, difficulty=self.difficulty)
        if not ok:
            return False, f"Блок невалиден: {msg}"

        self.chain.append(block)
        tx_ids = [tx.tx_id() for tx in block.transactions]
        self.mempool.remove_many(tx_ids)
        self._adjust_difficulty()
        return True, "OK"

    def total_work(self) -> int:
        return sum(2 ** self.difficulty for _ in self.chain)

    def replace_chain(self, new_chain: list, new_difficulty: int) -> tuple:
        if len(new_chain) <= len(self.chain):
            return False, "Новая цепочка не длиннее текущей"

        backup_chain = self.chain
        backup_difficulty = self.difficulty

        self.chain = new_chain
        self.difficulty = new_difficulty

        ok, msg = self.is_valid()
        if not ok:
            self.chain = backup_chain
            self.difficulty = backup_difficulty
            return False, f"Новая цепочка невалидна: {msg}"

        our_tx_ids = set()
        for b in backup_chain:
            for tx in b.transactions:
                if tx.sender != "COINBASE":
                    our_tx_ids.add(tx.tx_id())

        new_tx_ids = set()
        for b in new_chain:
            for tx in b.transactions:
                if tx.sender != "COINBASE":
                    new_tx_ids.add(tx.tx_id())

        orphaned_ids = our_tx_ids - new_tx_ids

        for b in backup_chain:
            for tx in b.transactions:
                if tx.tx_id() in orphaned_ids:
                    self.mempool.add(tx)

        return True, f"Цепочка заменена. Осиротевших: {len(orphaned_ids)}"

    def is_better_than(self, other: "Blockchain") -> bool:
        my_work = self.total_work()
        their_work = other.total_work()
        if my_work != their_work:
            return my_work > their_work
        return len(self.chain) > len(other.chain)

    def _adjust_difficulty(self) -> None:
        if len(self.chain) < config.DIFFICULTY_ADJUST_INTERVAL:
            return
        if len(self.chain) % config.DIFFICULTY_ADJUST_INTERVAL != 0:
            return

        recent = self.chain[-config.DIFFICULTY_ADJUST_INTERVAL:]
        time_taken = recent[-1].timestamp - recent[0].timestamp
        expected_time = (config.DIFFICULTY_ADJUST_INTERVAL - 1) * config.BLOCK_TIME_TARGET

        if time_taken < expected_time / 2:
            self.difficulty = min(self.difficulty + 1, config.MAX_DIFFICULTY)
        elif time_taken > expected_time * 2:
            self.difficulty = max(self.difficulty - 1, config.MIN_DIFFICULTY)

    # =========================================================================
    # БАЛАНСЫ (с учётом BURN)
    # =========================================================================

    def get_balance(self, address: str) -> int:
        """
        Баланс адреса. BURN-транзакции уменьшают баланс отправителя,
        но не прибавляются никому (монеты уничтожены).
        """
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address:
                    balance -= tx.amount + tx.fee
                # BURN-адрес не получает ничего
                if tx.recipient == address and tx.recipient != "BURN":
                    balance += tx.amount
        return balance

    def get_balance_aix(self, address: str) -> float:
        return self.get_balance(address) / config.SATOSHI

    def has_sufficient_balance(self, address: str, amount: int, fee: int = 0) -> bool:
        return self.get_balance(address) >= amount + fee

    def last_block(self) -> Block:
        return self.chain[-1]

    def height(self) -> int:
        return len(self.chain) - 1

    def total_transactions(self) -> int:
        return sum(len(b.transactions) for b in self.chain)

    def total_supply(self) -> int:
        """
        Сколько AIX в обращении.
        Учитывает: coinbase прибавляет, BURN отнимает.
        """
        total = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == "COINBASE":
                    total += tx.amount
                elif tx.sender == "LOTTERY":
                    total += tx.amount
                elif tx.recipient == "BURN":
                    total -= tx.amount
        return total

    def total_burned(self) -> int:
        """Сколько сожжено всего."""
        total = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == "BURN":
                    total += tx.amount
        return total

    def is_valid(self) -> tuple:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            ok, msg = current.is_valid(previous_block=previous, difficulty=self.difficulty)
            if not ok:
                return False, f"Блок #{i} невалиден: {msg}"
        return True, "OK"

    def to_dict(self) -> dict:
        return {
            "height": self.height(),
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain],
            "mempool": [tx.to_dict() for tx in self.mempool.transactions.values()],
        }

    def __repr__(self) -> str:
        return (
            f"Blockchain(height={self.height()}, "
            f"txs={self.total_transactions()}, "
            f"difficulty={self.difficulty}, "
            f"mempool={self.mempool.size()}, "
            f"work={self.total_work()})"
        )