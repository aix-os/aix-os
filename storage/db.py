"""
AIX OS — Хранилище блокчейна.

На MVP используем JSON — просто, читаемо, отлаживаемо.
Позже заменим на LevelDB, но интерфейс останется таким же.
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
import config

class ChainStorage:
    """Управляет сохранением и загрузкой цепочки."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def save(self, chain: Blockchain) -> None:
        """Сохранить всю цепочку (включая mempool) на диск."""
        data = chain.to_dict()
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
        # 🆕 Per-block: поднять текущую сложность до INITIAL, чтобы новые блоки были не ниже
        if chain.difficulty < config.INITIAL_DIFFICULTY:
            chain.difficulty = config.INITIAL_DIFFICULTY

        # Восстанавливаем mempool — критически важно!
        chain.mempool = Mempool()
        for tx_data in data.get("mempool", []):
            try:
                tx = Transaction.from_dict(tx_data)
                chain.mempool.add(tx)
            except Exception as e:
                print(f"⚠️  Не удалось восстановить транзакцию из mempool: {e}")

        # ✅ Инициализируем кэши (балансы, supply, валидность)
        chain._rebuild_cache()

        # ✅ Страховка: убираем из mempool всё, что уже в цепочке.
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