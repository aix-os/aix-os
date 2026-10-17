"""
AIX OS — Блок.

Блок = "контейнер для транзакций + штамп времени + ссылка на предыдущий блок".

Структура:
- index:         номер блока в цепочке (0 = генезис)
- timestamp:     когда создан
- transactions:  список транзакций внутри
- previous_hash: хеш предыдущего блока (ЭТО делает цепочку цепочкой)
- nonce:         число, которое подбирает майнер для PoW
- merkle_root:   хеш от всех транзакций (для быстрой проверки)
- hash:          хеш самого блока

Майнинг: подбираем nonce так, чтобы hash начинался с N нулей.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.hash import sha256, double_sha256, to_hex
from core.transaction import Transaction


# =============================================================================
# БЛОК
# =============================================================================

@dataclass
class Block:
    """Один блок AIX."""

    index: int                                  # Номер блока (0 = генезис)
    timestamp: float                            # Время создания
    transactions: list[Transaction] = field(default_factory=list)
    previous_hash: str = ""                     # Хеш предыдущего блока
    nonce: int = 0                              # Число для PoW
    hash: str = ""                              # Хеш этого блока
    merkle_root: str = ""                       # Хеш всех транзакций

    # =========================================================================
    # ХЕШИРОВАНИЕ
    # =========================================================================

    def calculate_hash(self) -> str:
        """
        Хеш блока = двойной SHA256 от (index, timestamp, merkle_root, prev_hash, nonce).

        САМО ПОЛЕ hash в расчёт НЕ ВХОДИТ — иначе получим бесконечную рекурсию.
        """
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "merkle_root": self.merkle_root,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        canonical = json.dumps(block_data, sort_keys=True, separators=(",", ":"))
        return double_sha256(canonical).hex()

    def compute_merkle_root(self) -> str:
        """
        Merkle root = хеш от всех транзакций в блоке.
        Позволяет быстро проверять, что транзакция в блоке.
        Для MVP — просто хеш от конкатенации tx_id.
        """
        if not self.transactions:
            return sha256(b"empty").hex()

        # Простая реализация (в будущем — настоящее Merkle-дерево)
        combined = "".join(tx.tx_id() for tx in self.transactions)
        return double_sha256(combined.encode("utf-8")).hex()

    # =========================================================================
    # МАЙНИНГ (Proof of Work)
    # =========================================================================

    def mine(self, difficulty: int) -> int:
        """
        Подобрать nonce так, чтобы hash начинался с `difficulty` нулей.

        Возвращает количество попыток (для статистики).
        """
        target_prefix = "0" * difficulty
        attempts = 0

        # Считаем merkle_root один раз до начала майнинга
        self.merkle_root = self.compute_merkle_root()

        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target_prefix):
                return attempts
            self.nonce += 1
            attempts += 1

    # =========================================================================
    # ВАЛИДАЦИЯ
    # =========================================================================

    def is_valid(self, previous_block: Optional["Block"] = None, difficulty: int = 4) -> tuple[bool, str]:
        """
        Проверка блока:
        1. Хеш блока действительно такой, как посчитано
        2. Хеш начинается с нужного числа нулей
        3. previous_hash совпадает с хешем прошлого блока
        4. Все транзакции валидны
        5. Merkle root совпадает
        """
        # 1. Хеш корректен
        if self.hash != self.calculate_hash():
            return False, "Хеш блока не соответствует содержимому"

        # 2. Сложность соблюдена
        if not self.hash.startswith("0" * difficulty):
            return False, f"Хеш не начинается с {difficulty} нулей"

        # 3. Ссылка на прошлый блок
        if previous_block is not None:
            if self.previous_hash != previous_block.hash:
                return False, "previous_hash не совпадает с хешем прошлого блока"
            if self.index != previous_block.index + 1:
                return False, "Неверный index блока"

        # 4. Все транзакции валидны
        for tx in self.transactions:
            ok, msg = tx.is_valid()
            if not ok:
                return False, f"Транзакция невалидна: {msg}"

        # 5. Merkle root
        if self.merkle_root != self.compute_merkle_root():
            return False, "Merkle root не совпадает"

        return True, "OK"

    # =========================================================================
    # СЕРИАЛИЗАЦИЯ
    # =========================================================================

    def to_dict(self) -> dict:
        """В словарь — транзакции тоже в словари."""
        d = asdict(self)
        d["transactions"] = [tx.to_dict() for tx in self.transactions]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        """Из словаря — восстановить блок."""
        data = data.copy()
        data["transactions"] = [
            Transaction.from_dict(tx) for tx in data.get("transactions", [])
        ]
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    # =========================================================================
    # ФАБРИКИ
    # =========================================================================

    @classmethod
    def create_genesis(cls, message: str = "AIX OS — Genesis Block") -> "Block":
        """
        Генезис-блок — первый блок цепочки.
        У него нет предыдущего хеша.
        """
        block = cls(
            index=0,
            timestamp=1735689600.0,  # 2025-01-01 00:00:00 UTC
            transactions=[],
            previous_hash="0" * 64,   # 64 нуля = "нет предыдущего"
        )
        block.merkle_root = block.compute_merkle_root()
        block.hash = block.calculate_hash()
        return block

    def __repr__(self) -> str:
        return (
            f"Block(#{self.index}, {len(self.transactions)} txs, "
            f"hash={self.hash[:12]}..., nonce={self.nonce})"
        )


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    from crypto.keys import generate_private_key
    from crypto.address import private_key_to_address

    print("🧱 Тестирую блоки AIX...\n")

    # Генезис
    genesis = Block.create_genesis("AIX OS — операционная система для жизни")
    print(f"🌱 Генезис: {genesis}")
    print(f"   Hash: {genesis.hash}")
    print()

    # Создаём пользователя и транзакцию
    alice_sk = generate_private_key()
    alice_addr = private_key_to_address(alice_sk)
    bob_sk = generate_private_key()
    bob_addr = private_key_to_address(bob_sk)

    tx = Transaction(
        sender=alice_addr,
        recipient=bob_addr,
        amount=100 * 10**8,
        message="Первый перевод в AIX!",
    )
    tx.sign_transaction(alice_sk)

    # Создаём второй блок
    print("⛏️  Майню блок #1 (сложность 4)...")
    block1 = Block(
        index=1,
        timestamp=time.time(),
        transactions=[tx],
        previous_hash=genesis.hash,
    )
    start = time.time()
    attempts = block1.mine(difficulty=4)
    elapsed = time.time() - start

    print(f"   {block1}")
    print(f"   Найдено за {attempts} попыток, {elapsed:.2f} сек")
    print()

    # Проверяем
    ok, msg = block1.is_valid(previous_block=genesis, difficulty=4)
    print(f"✅ Проверка блока #1: {ok} — {msg}\n")

    # Проверяем, что подделка провалится
    print("🕵️ Пытаюсь подделать данные в блоке...")
    block1.transactions[0].amount = 999999 * 10**8
    ok, msg = block1.is_valid(previous_block=genesis, difficulty=4)
    print(f"   Результат: {ok} — {msg}")
    print(f"   Ожидалось: False (хеш не сойдётся)\n")

    print("✅ Блоки работают.")