"""
AIX OS — Mempool.

Mempool (memory pool) — это очередь транзакций, которые ещё НЕ в блоке.
Когда пользователь отправляет AIX:
1. Транзакция летит в mempool.
2. Майнер берёт из mempool самые «жирные» (с высокой комиссией) и пакует в блок.
3. После включения в блок — транзакция уходит из mempool.

Mempool — временное хранилище. Он живёт в оперативной памяти ноды.
"""

import time
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.transaction import Transaction


# =============================================================================
# MEMPOOL
# =============================================================================

class Mempool:
    """Пул неподтверждённых транзакций."""

    def __init__(self, max_size: int = 5000):
        """
        max_size — максимальное число транзакций в пуле.
        При переполнении удаляются транзакции с минимальной комиссией.
        """
        self.transactions: dict[str, Transaction] = {}  # tx_id → Transaction
        self.max_size = max_size
        self.added_at: dict[str, float] = {}            # tx_id → время добавления

    # =========================================================================
    # ДОБАВЛЕНИЕ / УДАЛЕНИЕ
    # =========================================================================

    def add(self, tx: Transaction) -> tuple[bool, str]:
        """
        Добавить транзакцию в пул.
        Возвращает (True/False, причина).
        """
        # Проверяем валидность
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}"

        tx_id = tx.tx_id()

        # Не дубликат?
        if tx_id in self.transactions:
            return False, "Транзакция уже в пуле"

        # Не переполнен?
        if len(self.transactions) >= self.max_size:
            self._evict_cheapest()

        self.transactions[tx_id] = tx
        self.added_at[tx_id] = time.time()
        return True, "OK"

    def remove(self, tx_id: str) -> bool:
        """Удалить транзакцию из пула (например, после включения в блок)."""
        if tx_id in self.transactions:
            del self.transactions[tx_id]
            del self.added_at[tx_id]
            return True
        return False

    def remove_many(self, tx_ids: list[str]) -> int:
        """Удалить сразу много транзакций. Возвращает сколько удалено."""
        count = 0
        for tx_id in tx_ids:
            if self.remove(tx_id):
                count += 1
        return count

    def _evict_cheapest(self) -> None:
        """Удалить транзакцию с наименьшей комиссией (при переполнении)."""
        if not self.transactions:
            return
        cheapest_id = min(
            self.transactions.keys(),
            key=lambda tid: self.transactions[tid].fee,
        )
        self.remove(cheapest_id)

    # =========================================================================
    # ВЫБОРКА ДЛЯ БЛОКА
    # =========================================================================

    def select_for_block(self, max_count: int = 100) -> list[Transaction]:
        """
        Выбрать транзакции для нового блока.
        Сортировка: сначала высокая комиссия, потом старая.
        """
        sorted_txs = sorted(
            self.transactions.values(),
            key=lambda tx: (-tx.fee, self.added_at.get(tx.tx_id(), 0)),
        )
        return sorted_txs[:max_count]

    # =========================================================================
    # ПРОВЕРКА ДВОЙНОЙ ТРАТЫ
    # =========================================================================

    def has_conflict(self, tx: Transaction) -> bool:
        """
        Проверяет, не тратит ли эта транзакция те же средства,
        что уже заявлены в другой транзакции из пула (double-spend).
        """
        for existing in self.transactions.values():
            if existing.sender == tx.sender and existing.tx_id() != tx.tx_id():
                # Тот же отправитель уже есть в пуле — простая защита
                return True
        return False

    # =========================================================================
    # ИНФОРМАЦИЯ
    # =========================================================================

    def size(self) -> int:
        return len(self.transactions)

    def total_fees(self) -> int:
        """Суммарная комиссия всех транзакций в пуле (для майнера)."""
        return sum(tx.fee for tx in self.transactions.values())

    def clear(self) -> None:
        """Очистить пул."""
        self.transactions.clear()
        self.added_at.clear()

    def __repr__(self) -> str:
        return f"Mempool({self.size()} txs, fees={self.total_fees()})"


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    from crypto.keys import generate_private_key
    from crypto.address import private_key_to_address

    print("📬 Тестирую Mempool...\n")

    mempool = Mempool(max_size=5)

    # Создаём пользователей
    alice_sk = generate_private_key()
    alice_addr = private_key_to_address(alice_sk)
    bob_sk = generate_private_key()
    bob_addr = private_key_to_address(bob_sk)

    # Добавляем 3 транзакции с разными комиссиями
    print("📥 Добавляю транзакции...")
    for i, fee in enumerate([0, 5, 10]):
        tx = Transaction(
            sender=alice_addr,
            recipient=bob_addr,
            amount=(i + 1) * 10**8,
            fee=fee,
            message=f"Транзакция #{i + 1}",
        )
        tx.sign_transaction(alice_sk)
        ok, msg = mempool.add(tx)
        print(f"   TX#{i + 1} (fee={fee}): {ok} — {msg}")

    print(f"\n📊 Mempool: {mempool}\n")

    # Выбираем транзакции для блока — должны быть по убыванию комиссии
    print("🔝 Выбираю для блока (по убыванию комиссии):")
    selected = mempool.select_for_block(max_count=10)
    for tx in selected:
        print(f"   fee={tx.fee}, amount={tx.amount // 10**8} AIX")

    print(f"\n✅ Mempool работает.")