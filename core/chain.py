"""
AIX OS — Блокчейн (цепочка блоков).

Особенность: транзакции с recipient="BURN" уменьшают supply (сжигание).
С кэшированием балансов и валидности для высокой производительности.
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
        
        # Кэши для быстрого доступа
        self._balances: dict[str, int] = {}
        self._total_supply: int = 0
        self._total_burned: int = 0
        self._is_valid_cache: tuple[bool, str] = (True, "OK")
        self._is_valid_height: int = 0
        
        self._create_genesis()

    def _create_genesis(self) -> None:
        genesis = Block.create_genesis(config.GENESIS_MESSAGE)
        self.chain.append(genesis)
        self._apply_block_to_cache(genesis)
        self._is_valid_height = 0

    def ensure_premine(self) -> None:
        """Кладёт pre-mine tx в мемпул (закроется следующим /mine)."""
        try:
            from core import vesting
        except Exception:
            return
        addr = vesting.AIX_DEV_ADDRESS
        if addr is None:
            return
        
        # 1. Проверка: уже в балансе (в блокчейне)?
        current = self._balances.get(addr, 0)
        if current >= vesting.AIX_DEV_TOTAL_RAW:
            print(f"[premine] AIX-DEV уже имеет {current/100000000:.2f} AIX в блокчейне, скип")
            return
        
        # 2. Проверка: уже в мемпуле (ждёт майнинга)?
        for tx in self.mempool.transactions.values():
            if tx.sender == "COINBASE" and tx.recipient == addr:
                print(f"[premine] tx уже в мемпуле, ждёт майнинга, скип")
                return

        from core.transaction import Transaction
        import time as _t
        tx = Transaction(
            sender="COINBASE",
            recipient=addr,
            amount=vesting.AIX_DEV_TOTAL_RAW,
            timestamp=_t.time(),
            fee=0,
            message="AIX OS Foundation Reserve (Vesting 4y)",
        )
        ok, msg = tx.is_valid()
        if not ok:
            print(f"[premine] tx invalid: {msg}")
            return
        ok, msg = self.mempool.add(tx)
        if ok:
            print(f"[premine] ✅ tx в мемпуле: {vesting.AIX_DEV_TOTAL_AIX} AIX → AIX-DEV")
        else:
            print(f"[premine] ❌ mempool.add: {msg}")


    def _apply_block_to_cache(self, block: Block) -> None:
        """Обновляет балансы и статистику на основе нового блока."""
        for tx in block.transactions:
            # Балансы
            self._balances[tx.sender] = self._balances.get(tx.sender, 0) - tx.amount - tx.fee
            if tx.recipient != "BURN":
                self._balances[tx.recipient] = self._balances.get(tx.recipient, 0) + tx.amount
            
            # Supply
            if tx.sender == "COINBASE" or tx.sender == "LOTTERY":
                self._total_supply += tx.amount
            elif tx.recipient == "BURN":
                self._total_supply -= tx.amount
                self._total_burned += tx.amount

    def _rebuild_cache(self) -> None:
        """Полностью пересобирает кэш (при загрузке с диска)."""
        self._balances = {}
        self._total_supply = 0
        self._total_burned = 0
        for block in self.chain:
            self._apply_block_to_cache(block)
        self._is_valid_height = self.height()
        self._is_valid_cache = (True, "OK")
        self.ensure_premine()

    def add_block(self, block: Block) -> tuple:
        previous_block = self.last_block()
        # 🆕 Per-block difficulty: новый блок наследует текущую сложность
        if block.difficulty == 0:
            block.difficulty = self.difficulty
        ok, msg = block.is_valid(previous_block=previous_block, difficulty=block.difficulty)
        if not ok:
            return False, f"Блок невалиден: {msg}"

        self.chain.append(block)
        self._apply_block_to_cache(block)
        
        tx_ids = [tx.tx_id() for tx in block.transactions]
        self.mempool.remove_many(tx_ids)
        if hasattr(self, '_rebuild_cache'):
            self._rebuild_cache()
        self._adjust_difficulty()
        
        # Обновляем кэш валидности
        if self._is_valid_cache[0]:
            self._is_valid_cache = (True, "OK")
            self._is_valid_height = self.height()
        else:
            self._is_valid_height = -1
            
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
        
        # Принудительная полная проверка
        self._is_valid_height = -1
        self._is_valid_cache = (False, "Не проверено")

        ok, msg = self.is_valid()
        if not ok:
            self.chain = backup_chain
            self.difficulty = backup_difficulty
            self._rebuild_cache()
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

        if new_tx_ids:
            self.mempool.remove_many(list(new_tx_ids))

        orphaned_ids = our_tx_ids - new_tx_ids
        for b in backup_chain:
            for tx in b.transactions:
                if tx.tx_id() in orphaned_ids:
                    self.mempool.add(tx)
                    
        self._rebuild_cache()
        return True, f"Цепочка заменена. Из mempool удалено: {len(new_tx_ids)}, осиротевших: {len(orphaned_ids)}"

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
    # БАЛАНСЫ (ИЗ КЭША)
    # =========================================================================

    def get_balance(self, address: str) -> int:
        return self._balances.get(address, 0)

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
        return self._total_supply

    def total_burned(self) -> int:
        return self._total_burned

    def is_valid(self) -> tuple:
        if self._is_valid_height == self.height():
            return self._is_valid_cache
            
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            ok, msg = current.is_valid(previous_block=previous, difficulty=self.difficulty)
            if not ok:
                self._is_valid_cache = (False, msg)
                self._is_valid_height = -1
                return False, f"Блок #{i} невалиден: {msg}"
                
        self._is_valid_cache = (True, "OK")
        self._is_valid_height = self.height()
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