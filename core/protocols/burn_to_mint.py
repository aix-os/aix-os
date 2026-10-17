"""
AIX OS — Burn-to-Mint (#5).

Сожги AIX — получи уникальный NFT-артефакт.

Как работает:
1. Пользователь выбирает уровень (COMMON, UNCOMMON, RARE, LEGENDARY, MYTHIC)
2. Создаётся BURN-транзакция: sender → "BURN" на нужное количество AIX
3. Монеты исчезают из supply (BURN-адрес не учитывается в балансах)
4. Создаётся артефакт с уникальным ID, привязанный к адресу
5. Артефакт 1 из 1 — больше никто такой не получит

Хранение: data/burn_artifacts.json

Каждый артефакт имеет:
- Уровень (COMMON, UNCOMMON, RARE, LEGENDARY, MYTHIC)
- Порядковый номер (#1, #2, #3...)
- Владельца (AIX-адрес)
- Метаданные (имя, эмодзи, описание)
"""

import json
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transaction import Transaction
from core.wallet import Wallet
from crypto.address import is_valid_address
import config


# =============================================================================
# КАТАЛОГ АРТЕФАКТОВ
# =============================================================================

BURN_CATALOG = {
    "COMMON": {
        "name": "Уголёк",
        "emoji": "🔥",
        "description": "Тлеющий осколок, рождённый из сожжённых монет",
        "price_aix": 100,
        "rarity": "common",
    },
    "UNCOMMON": {
        "name": "Искра",
        "emoji": "✨",
        "description": "Яркая вспышка, способная зажечь пламя",
        "price_aix": 500,
        "rarity": "uncommon",
    },
    "RARE": {
        "name": "Пламя",
        "emoji": "🕯️",
        "description": "Живой огонь, который не гаснет во времени",
        "price_aix": 1000,
        "rarity": "rare",
    },
    "LEGENDARY": {
        "name": "Пепел Феникса",
        "emoji": "🐦‍🔥",
        "description": "Оставшийся от птицы, что возрождается из пепла",
        "price_aix": 5000,
        "rarity": "legendary",
    },
    "MYTHIC": {
        "name": "Сердце Звезды",
        "emoji": "💫",
        "description": "Ядро умершей звезды. Светит вечно.",
        "price_aix": 10000,
        "rarity": "mythic",
    },
}


# =============================================================================
# АРТЕФАКТ
# =============================================================================

@dataclass
class BurnArtifact:
    """Один артефакт, полученный за сжигание AIX."""
    id: str                          # уникальный ID (например "UG-001")
    level: str                       # COMMON, UNCOMMON, ...
    serial: int                      # порядковый номер в уровне (1, 2, 3...)
    owner: str                       # AIX-адрес владельца
    amount_burned: int               # сколько сожжено (в атомарных единицах)
    name: str                        # "Уголёк #1"
    emoji: str
    description: str
    rarity: str
    created_at: float
    burn_tx_id: str = ""             # ID BURN-транзакции (для истории)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BurnArtifact":
        return cls(**data)

    def __repr__(self):
        return f"BurnArtifact({self.id}, {self.emoji} {self.name}@{self.owner[:16]}...)"


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class BurnToMintManager:
    """Менеджер артефактов. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.artifacts: dict[str, BurnArtifact] = {}  # id -> Artifact
        self._serial_counters: dict[str, int] = {k: 0 for k in BURN_CATALOG}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("artifacts", []):
                a = BurnArtifact.from_dict(item)
                self.artifacts[a.id] = a
                # Обновляем счётчик
                if a.serial > self._serial_counters.get(a.level, 0):
                    self._serial_counters[a.level] = a.serial
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить артефакты: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"artifacts": [a.to_dict() for a in self.artifacts.values()]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # СОЗДАНИЕ (BURN → MINT)
    # =========================================================================

    def mint(self, owner: str, level: str, private_key: str = "",
             blockchain=None) -> tuple[bool, str, Optional[BurnArtifact]]:
        """
        Сжечь AIX и получить артефакт.
        Возвращает (успех, сообщение, артефакт).
        """
        level = level.upper()

        if level not in BURN_CATALOG:
            return False, f"Неизвестный уровень '{level}'. Доступные: {', '.join(BURN_CATALOG.keys())}", None

        if not is_valid_address(owner):
            return False, "Невалидный AIX-адрес", None

        info = BURN_CATALOG[level]
        price_raw = info["price_aix"] * config.SATOSHI

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна для сжигания", None

        # Проверяем баланс
        balance = bc.get_balance(owner)
        if balance < price_raw:
            return False, (f"Недостаточно AIX. Нужно: {info['price_aix']}, "
                          f"у вас: {balance / config.SATOSHI:.2f}"), None

        # Ищем кошелёк владельца локально
        import ecdsa
        if private_key:
            sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
        else:
            owner_wallet = self._find_wallet(owner)
            if owner_wallet is None:
                return False, "Локальный кошелёк не найден", None
            sk = owner_wallet.get_signing_key()

        # Создаём BURN-транзакцию
        tx = Transaction(
            sender=owner,
            recipient="BURN",
            amount=price_raw,
            message=f"🔥 Burn-to-Mint: {info['name']}",
        )
        tx.sign_transaction(sk)
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}", None
        ok, msg = bc.mempool.add(tx)
        if not ok:
            return False, f"Не добавлено в mempool: {msg}", None

        # Создаём артефакт
        self._serial_counters[level] = self._serial_counters.get(level, 0) + 1
        serial = self._serial_counters[level]

        # ID вида "COM-001", "RAR-007" и т.д.
        level_short = level[:3]
        artifact_id = f"{level_short}-{serial:03d}"

        artifact = BurnArtifact(
            id=artifact_id,
            level=level,
            serial=serial,
            owner=owner,
            amount_burned=price_raw,
            name=f"{info['name']} #{serial}",
            emoji=info["emoji"],
            description=info["description"],
            rarity=info["rarity"],
            created_at=time.time(),
            burn_tx_id=tx.tx_id(),
        )
        self.artifacts[artifact_id] = artifact
        self._save()

        return True, tx.tx_id(), artifact

    # =========================================================================
    # ПРОСМОТР
    # =========================================================================

    def get(self, artifact_id: str) -> Optional[BurnArtifact]:
        return self.artifacts.get(artifact_id.upper())

    def list_by_owner(self, address: str) -> list:
        return sorted(
            [a for a in self.artifacts.values() if a.owner == address],
            key=lambda a: a.created_at,
        )

    def list_by_level(self, level: str) -> list:
        level = level.upper()
        return sorted(
            [a for a in self.artifacts.values() if a.level == level],
            key=lambda a: a.serial,
        )

    def total_burned(self) -> int:
        """Всего сожжено AIX (в атомарных единицах)."""
        return sum(a.amount_burned for a in self.artifacts.values())

    def total_burned_aix(self) -> float:
        return self.total_burned() / config.SATOSHI

    def stats_by_level(self) -> dict:
        result = {}
        for level, info in BURN_CATALOG.items():
            count = sum(1 for a in self.artifacts.values() if a.level == level)
            burned_raw = sum(a.amount_burned for a in self.artifacts.values() if a.level == level)
            result[level] = {
                "name": info["name"],
                "emoji": info["emoji"],
                "price_aix": info["price_aix"],
                "rarity": info["rarity"],
                "issued": count,
                "burned_aix": burned_raw / config.SATOSHI,
            }
        return result

    def leaderboard(self, limit: int = 20) -> list:
        """
        Топ коллекционеров: (address, total_artifacts, rare_count, burned_aix).
        """
        from collections import defaultdict
        scores = defaultdict(lambda: {"count": 0, "rare": 0, "burned": 0})
        rarity_weight = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 3, "mythic": 4}

        for a in self.artifacts.values():
            s = scores[a.owner]
            s["count"] += 1
            s["burned"] += a.amount_burned
            if a.rarity in ("rare", "legendary", "mythic"):
                s["rare"] += 1

        sorted_items = sorted(
            scores.items(),
            key=lambda kv: (-kv[1]["rare"], -kv[1]["count"], -kv[1]["burned"])
        )
        return [
            (addr, s["count"], s["rare"], s["burned"] / config.SATOSHI)
            for addr, s in sorted_items[:limit]
        ]

    # =========================================================================
    # СИНХРОНИЗАЦИЯ
    # =========================================================================

    def export_all(self) -> list:
        return [a.to_dict() for a in self.artifacts.values()]

    def import_artifact(self, data: dict) -> tuple[bool, str]:
        """Merge одного артефакта. Артефакты уникальны по ID — merge простой."""
        try:
            new_a = BurnArtifact.from_dict(data)
        except Exception as e:
            return False, f"Ошибка парсинга: {e}"

        if new_a.id in self.artifacts:
            return True, "уже есть"

        self.artifacts[new_a.id] = new_a
        if new_a.serial > self._serial_counters.get(new_a.level, 0):
            self._serial_counters[new_a.level] = new_a.serial
        self._save()
        return True, "добавлен"

    # =========================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # =========================================================================

    @staticmethod
    def _find_wallet(address: str) -> Optional[Wallet]:
        for name in Wallet.list_wallets():
            try:
                w = Wallet.load(name)
                if w.address == address:
                    return w
            except Exception:
                continue
        return None

    def __len__(self):
        return len(self.artifacts)

    def __repr__(self):
        return f"BurnToMintManager({len(self.artifacts)} artifacts)"