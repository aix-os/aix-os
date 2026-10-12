"""
AIX OS — Soul-Bound Tokens (#11).

Медали чести — непередаваемые токены репутации.

Особенности:
1. Привязаны к адресу НАВСЕГДА — нельзя передать через send/gift/timelock
2. Выдаются только по правилам каталога медалей
3. Могут быть отозваны только в исключительных случаях (по решению foundation)
4. Видны публично в профиле адреса

Хранение: data/sbt.json

Каталог медалей — заранее определённый набор достижений.
"""

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


# =============================================================================
# КАТАЛОГ МЕДАЛЕЙ (предустановленный набор)
# =============================================================================

MEDAL_CATALOG = {
    "FOUNDER": {
        "title": "Основатель",
        "emoji": "👑",
        "description": "Тот, кто начал Империю. Один на всех.",
        "rarity": "legendary",
        "max_supply": 1,
    },
    "EARLY_BIRD": {
        "title": "Ранняя птица",
        "emoji": "🐣",
        "description": "Один из первых 100 в системе",
        "rarity": "rare",
        "max_supply": 100,
    },
    "CONTRIBUTOR": {
        "title": "Творец",
        "emoji": "🛠️",
        "description": "Внёс вклад в код или документацию",
        "rarity": "uncommon",
        "max_supply": None,
    },
    "TRANSLATOR": {
        "title": "Толмач",
        "emoji": "🌍",
        "description": "Перевёл документацию или интерфейс",
        "rarity": "uncommon",
        "max_supply": None,
    },
    "BUG_HUNTER": {
        "title": "Ловчий Багов",
        "emoji": "🐛",
        "description": "Нашёл и сообщил о баге",
        "rarity": "uncommon",
        "max_supply": None,
    },
    "GUARDIAN": {
        "title": "Хранитель",
        "emoji": "🛡️",
        "description": "Защитил сеть от атаки",
        "rarity": "rare",
        "max_supply": None,
    },
    "COMMUNITY": {
        "title": "Голос Сообщества",
        "emoji": "🗣️",
        "description": "Активно помогает новичкам",
        "rarity": "common",
        "max_supply": None,
    },
    "VETERAN_1Y": {
        "title": "Ветеран",
        "emoji": "⚔️",
        "description": "Один год в AIX OS",
        "rarity": "uncommon",
        "max_supply": None,
    },
    "VETERAN_5Y": {
        "title": "Старший Ветеран",
        "emoji": "🎖️",
        "description": "Пять лет в AIX OS",
        "rarity": "rare",
        "max_supply": None,
    },
    "LEGEND": {
        "title": "Легенда Сообщества",
        "emoji": "🌟",
        "description": "Тот, кого знают все. Вне времени.",
        "rarity": "legendary",
        "max_supply": None,
    },
}


# =============================================================================
# МЕДАЛЬ (конкретная выдача)
# =============================================================================

@dataclass
class Medal:
    """Конкретная выдача медали конкретному адресу."""
    medal_id: str                # ключ из MEDAL_CATALOG
    owner: str                   # AIX-адрес владельца
    issuer: str                  # кто выдал (AIX-адрес)
    reason: str                  # за что
    issued_at: float
    revoked: bool = False
    revoked_at: float = 0.0
    revoked_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Medal":
        return cls(**data)

    def catalog_info(self) -> dict:
        return MEDAL_CATALOG.get(self.medal_id, {})

    def title(self) -> str:
        return self.catalog_info().get("title", self.medal_id)

    def emoji(self) -> str:
        return self.catalog_info().get("emoji", "🏅")

    def rarity(self) -> str:
        return self.catalog_info().get("rarity", "common")

    def __repr__(self):
        return f"Medal({self.medal_id}@{self.owner[:12]}...)"


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class SBTManager:
    """Менеджер медалей. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.medals: list[Medal] = []
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("medals", []):
                self.medals.append(Medal.from_dict(item))
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Не удалось загрузить SBT: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"medals": [m.to_dict() for m in self.medals]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # ВЫДАЧА
    # =========================================================================

    def award(self, medal_id: str, owner: str, issuer: str,
              reason: str = "") -> tuple[bool, str, Optional[Medal]]:
        """
        Выдать медаль. Возвращает (успех, сообщение, медаль).
        """
        if medal_id not in MEDAL_CATALOG:
            return False, f"Медаль '{medal_id}' не найдена в каталоге", None

        info = MEDAL_CATALOG[medal_id]

        # Проверяем лимит supply
        max_supply = info.get("max_supply")
        if max_supply is not None:
            issued = sum(1 for m in self.medals
                        if m.medal_id == medal_id and not m.revoked)
            if issued >= max_supply:
                return False, (f"Достигнут лимит медали '{info['title']}' "
                              f"({issued}/{max_supply})"), None

        # Проверяем, не выдана ли уже такая же этому адресу
        already = any(m for m in self.medals
                     if m.medal_id == medal_id and m.owner == owner and not m.revoked)
        if already:
            return False, f"Медаль '{info['title']}' уже есть у {owner[:20]}...", None

        medal = Medal(
            medal_id=medal_id,
            owner=owner,
            issuer=issuer,
            reason=reason,
            issued_at=time.time(),
        )
        self.medals.append(medal)
        self._save()
        return True, "OK", medal

    # =========================================================================
    # ОТЗЫВ (только в исключительных случаях)
    # =========================================================================

    def revoke(self, medal_id: str, owner: str,
               reason: str = "") -> tuple[bool, str]:
        for m in self.medals:
            if m.medal_id == medal_id and m.owner == owner and not m.revoked:
                m.revoked = True
                m.revoked_at = time.time()
                m.revoked_reason = reason
                self._save()
                return True, "OK"
        return False, "Медаль не найдена или уже отозвана"

    # =========================================================================
    # ПРОСМОТР
    # =========================================================================

    def medals_of(self, address: str) -> list[Medal]:
        """Все активные медали адреса."""
        return [m for m in self.medals
                if m.owner == address and not m.revoked]

    def medals_issued_by(self, address: str) -> list[Medal]:
        """Все медали, выданные этим адресом."""
        return [m for m in self.medals
                if m.issuer == address and not m.revoked]

    def count_by_medal_id(self, medal_id: str) -> int:
        return sum(1 for m in self.medals
                   if m.medal_id == medal_id and not m.revoked)

    def reputation(self, address: str) -> int:
        """
        Репутация = сумма весов медалей.
        common=1, uncommon=3, rare=10, legendary=50.
        """
        weights = {"common": 1, "uncommon": 3, "rare": 10, "legendary": 50}
        return sum(weights.get(m.rarity(), 1) for m in self.medals_of(address))

    def leaderboard(self, limit: int = 20) -> list[tuple[str, int, int]]:
        """
        Топ адресов по репутации.
        Возвращает список (address, reputation, medal_count).
        """
        from collections import defaultdict
        scores: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        weights = {"common": 1, "uncommon": 3, "rare": 10, "legendary": 50}
        for m in self.medals:
            if m.revoked:
                continue
            scores[m.owner][0] += weights.get(m.rarity(), 1)
            scores[m.owner][1] += 1
        sorted_items = sorted(scores.items(),
                              key=lambda kv: (-kv[1][0], -kv[1][1]))
        return [(addr, v[0], v[1]) for addr, v in sorted_items[:limit]]

    def __len__(self):
        return len([m for m in self.medals if not m.revoked])

    def __repr__(self):
        return f"SBTManager({len(self)} medals)"