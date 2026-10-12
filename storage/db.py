"""
AIX OS — Хранилище блокчейна.

На MVP используем JSON — просто, читаемо, отлаживаемо.
Позже заменим на LevelDB, но интерфейс останется таким же.

Файл: data/chain.json

ВАЖНО: сохраняем и цепочку блоков, и mempool (очередь транзакций).
Иначе транзакции будут теряться между запусками CLI.

ДОПОЛНИТЕЛЬНО: при загрузке автоочищаем mempool от stale-tx
(тех, что уже вошли в цепочку). Это защита от ручных правок JSON
и от багов синхронизации.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.block import Block
from core.chain import Blockchain
from core.transaction import Transaction
from core.mempool import Mempool


# =============================================================================
# СОХРАНЕНИЕ / ЗАГРУЗКА ЦЕПОЧКИ
# =============================================================================

class ChainStorage:
    """Управляет сохранением и загрузкой цепочки."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def save(self, chain: Blockchain) -> None:
        """Сохранить всю цепочку (включая mempool) на диск."""
        data = chain.to_dict()
        # Атомарная запись — сначала во временный файл, потом переименование
        # Это защищает от повреждения при сбое
        tmp_path = self.filepath.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.filepath)

    def load(self) -> Optional[Blockchain]:
        """
        Загрузить цепочку с диска. Возвращает None, если файла нет.

        Автоочистка: убираем из mempool всё, что уже вошло в цепочку.
        """
        if not self.filepath.exists():
            return None

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Не удалось загрузить цепочку: {e}")
            return None

        # Восстанавливаем блокчейн без вызова __init__ (он создал бы новый генезис)
        chain = Blockchain.__new__(Blockchain)
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        chain.difficulty = data.get("difficulty", 4)

        # Восстанавливаем mempool — критически важно!
        chain.mempool = Mempool()
        for tx_data in data.get("mempool", []):
            try:
                tx = Transaction.from_dict(tx_data)
                chain.mempool.add(tx)
            except Exception as e:
                print(f"⚠️  Не удалось восстановить транзакцию из mempool: {e}")

        # ✅ Страховка: убираем из mempool всё, что уже в цепочке.
        # Защищает от stale-tx после ручного редактирования data/*.json
        # или от багов синхронизации.
        included_ids = set()
        for block in chain.chain:
            for tx in block.transactions:
                included_ids.add(tx.tx_id())
        if included_ids:
            removed = chain.mempool.remove_many(list(included_ids))
            if removed:
                print(f"ℹ️  Автоочистка mempool: удалено {removed} stale-tx")

        return chain

    def exists(self) -> bool:
        return self.filepath.exists()

    def delete(self) -> None:
        """Удалить файл с цепочкой (для тестов)."""
        if self.filepath.exists():
            self.filepath.unlink()


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    import time
    from crypto.keys import generate_private_key
    from crypto.address import private_key_to_address
    import config

    print("💾 Тестирую хранилище (с сохранением mempool)...\n")

    test_path = Path("data/test_chain.json")
    storage = ChainStorage(test_path)

    # Удаляем старый тест
    storage.delete()

    # ===== Создаём цепочку =====
    print("1. Создаю цепочку с блоком и транзакцией в mempool...")
    chain = Blockchain()
    miner_sk = generate_private_key()
    miner_addr = private_key_to_address(miner_sk)

    alice_sk = generate_private_key()
    alice_addr = private_key_to_address(alice_sk)

    # Блок с coinbase
    coinbase = Transaction.create_coinbase(
        recipient=miner_addr,
        amount=config.INITIAL_BLOCK_REWARD * config.SATOSHI,
    )
    block1 = Block(
        index=1,
        timestamp=time.time(),
        transactions=[coinbase],
        previous_hash=chain.last_block().hash,
    )
    block1.mine(difficulty=chain.difficulty)
    chain.add_block(block1)

    # Транзакция в mempool (ещё не в блоке!)
    tx = Transaction(
        sender=miner_addr,
        recipient=alice_addr,
        amount=10 * config.SATOSHI,
        message="Тест сохранения mempool",
    )
    tx.sign_transaction(miner_sk)
    chain.mempool.add(tx)

    print(f"   Высота: {chain.height()}")
    print(f"   Mempool: {chain.mempool.size()} транзакция")
    print(f"   Баланс майнера: {chain.get_balance_aix(miner_addr):.2f} AIX\n")

    # ===== Сохраняем =====
    print("2. Сохраняю на диск...")
    storage.save(chain)
    size = test_path.stat().st_size
    print(f"   Файл: {test_path} ({size} байт)\n")

    # ===== Загружаем =====
    print("3. Загружаю с диска в новую переменную...")
    loaded = storage.load()
    print(f"   Высота: {loaded.height()}")
    print(f"   Mempool: {loaded.mempool.size()} транзакция")
    print(f"   Баланс майнера: {loaded.get_balance_aix(miner_addr):.2f} AIX\n")

    # ===== Проверяем, что mempool восстановился =====
    print("4. Проверка mempool:")
    if loaded.mempool.size() == 1:
        print(f"   ✅ Mempool восстановлен — {loaded.mempool.size()} транзакция")
        tx_loaded = list(loaded.mempool.transactions.values())[0]
        print(f"   TX ID: {tx_loaded.tx_id()[:32]}...")
        print(f"   Сумма: {tx_loaded.amount // config.SATOSHI} AIX")
    else:
        print(f"   ❌ ПРОВАЛ: mempool пуст (должно быть 1)")

    # ===== Проверяем валидность =====
    ok, msg = loaded.is_valid()
    print(f"\n5. Целостность загруженной цепочки: {ok} — {msg}\n")

    # ===== Удаляем тест =====
    storage.delete()
    print("✅ Хранилище работает корректно (с mempool).")