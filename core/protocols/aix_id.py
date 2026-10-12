"""
AIX OS — AIX-ID (#137).

Паспорт Творца. Публичное имя + профиль, привязанные к AIX-адресу.

Что это:
- Имя вида 'alice' (3-20 символов: a-z, 0-9, _)
- Аватар — эмодзи или URL картинки
- Bio — короткое описание
- Публичный профиль с репутацией и медалями

Зачем:
- Вместо AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC → просто "alice"
- Можно отправлять по имени: aix send alice bob 10
- Репутация и медали видны всем
- Основа для AIX Contacts (телефонная книга)

Хранение: data/aix_ids.json
"""

import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crypto.address import is_valid_address
import config


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 20
# Только строчные буквы, цифры, подчёркивание. Не может начинаться с цифры/_
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,19}$")

# Зарезервированные имена — нельзя регистрировать
RESERVED_NAMES = {
    "aix", "admin", "root", "system", "official",
    "aixos", "coinbase", "lottery", "null", "undefined",
    "bot", "support", "help", "mod", "moderator",
}

# Максимальная длина bio и display_name
BIO_MAX = 200
DISPLAY_MAX = 40


# =============================================================================
# ПРОФИЛЬ
# =============================================================================

@dataclass
class AIXProfile:
    """Публичный профиль адреса."""
    name: str                       # "alice" — уникальное имя
    address: str                    # AIX-адрес
    display_name: str = ""          # "Алиса Иванова" — человекочитаемое
    avatar: str = ""                # эмодзи или URL
    bio: str = ""                   # короткое описание
    created_at: float = 0.0
    updated_at: float = 0.0
    verified: bool = False          # подтверждён основателем (для будущего)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AIXProfile":
        return cls(**data)

    def __repr__(self):
        return f"AIXProfile({self.name}@{self.address[:16]}...)"


# =============================================================================
# ВАЛИДАЦИЯ ИМЕНИ
# =============================================================================

def validate_name(name: str) -> tuple[bool, str]:
    """Проверяет имя. Возвращает (ок, сообщение)."""
    name = name.lower().strip()

    if len(name) < NAME_MIN_LENGTH:
        return False, f"Минимум {NAME_MIN_LENGTH} символа"
    if len(name) > NAME_MAX_LENGTH:
        return False, f"Максимум {NAME_MAX_LENGTH} символов"
    if not NAME_PATTERN.match(name):
        return False, ("Только строчные a-z, цифры и _; "
                       "первый символ — буква")
    if name in RESERVED_NAMES:
        return False, f"Имя '{name}' зарезервировано"
    return True, "OK"


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class AIXIDManager:
    """Менеджер AIX-ID."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.profiles: dict[str, AIXProfile] = {}    # name -> Profile
        self._by_address: dict[str, AIXProfile] = {} # address -> Profile
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("profiles", []):
                p = AIXProfile.from_dict(item)
                self.profiles[p.name] = p
                self._by_address[p.address] = p
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить AIX-ID: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"profiles": [p.to_dict() for p in self.profiles.values()]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # РЕГИСТРАЦИЯ
    # =========================================================================

    def register(self, address: str, name: str,
                 display_name: str = "", avatar: str = "",
                 bio: str = "") -> tuple:
        """Зарегистрировать AIX-ID. Возвращает (ок, сообщение, профиль)."""
        name = name.lower().strip()

        if not is_valid_address(address):
            return False, "Невалидный AIX-адрес", None

        ok, msg = validate_name(name)
        if not ok:
            return False, msg, None

        if name in self.profiles:
            return False, f"Имя '{name}' уже занято", None

        if address in self._by_address:
            return False, (f"Адрес уже имеет ID: "
                          f"{self._by_address[address].name}"), None

        if display_name and len(display_name) > DISPLAY_MAX:
            return False, f"Display name слишком длинный (макс {DISPLAY_MAX})", None
        if bio and len(bio) > BIO_MAX:
            return False, f"Bio слишком длинное (макс {BIO_MAX})", None

        now = time.time()
        profile = AIXProfile(
            name=name,
            address=address,
            display_name=display_name or name,
            avatar=avatar or "👤",
            bio=bio,
            created_at=now,
            updated_at=now,
        )
        self.profiles[name] = profile
        self._by_address[address] = profile
        self._save()
        return True, "OK", profile

    # =========================================================================
    # ОБНОВЛЕНИЕ
    # =========================================================================

    def update(self, address: str,
               display_name: Optional[str] = None,
               avatar: Optional[str] = None,
               bio: Optional[str] = None) -> tuple:
        profile = self._by_address.get(address)
        if profile is None:
            return False, "У адреса нет AIX-ID", None

        if display_name is not None:
            if len(display_name) > DISPLAY_MAX:
                return False, f"Display name макс {DISPLAY_MAX}", None
            profile.display_name = display_name

        if avatar is not None:
            profile.avatar = avatar

        if bio is not None:
            if len(bio) > BIO_MAX:
                return False, f"Bio макс {BIO_MAX}", None
            profile.bio = bio

        profile.updated_at = time.time()
        self._save()
        return True, "OK", profile

    # =========================================================================
    # ПОИСК
    # =========================================================================

    def get_by_name(self, name: str) -> Optional[AIXProfile]:
        return self.profiles.get(name.lower().strip())

    def get_by_address(self, address: str) -> Optional[AIXProfile]:
        return self._by_address.get(address)

    def resolve(self, name_or_address: str) -> Optional[str]:
        """
        Умный resolve: имя, @имя или AIX-адрес → AIX-адрес.
        Используется везде, где CLI принимает `who`.
        """
        s = name_or_address.strip()

        # Убираем ведущий @
        if s.startswith("@"):
            s = s[1:]

        # Если это AIX-адрес — возвращаем как есть
        if is_valid_address(s):
            return s

        # Если это имя — ищем профиль
        profile = self.get_by_name(s)
        if profile:
            return profile.address

        return None

    def list_all(self, limit: Optional[int] = None) -> list:
        profiles = sorted(self.profiles.values(), key=lambda p: p.created_at)
        if limit:
            return profiles[:limit]
        return profiles

    def count(self) -> int:
        return len(self.profiles)

    # =========================================================================
    # ИМПОРТ/ЭКСПОРТ (для state sync)
    # =========================================================================

    def export_all(self) -> list:
        return [p.to_dict() for p in self.profiles.values()]

    def import_profile(self, data: dict) -> tuple:
        """Merge одного профиля. Более свежий updated_at побеждает."""
        try:
            new_p = AIXProfile.from_dict(data)
        except Exception as e:
            return False, f"Ошибка парсинга: {e}"

        existing = self.profiles.get(new_p.name)
        if existing is None:
            # Проверяем, нет ли уже профиля для этого адреса
            existing_addr = self._by_address.get(new_p.address)
            if existing_addr:
                # Адрес занят другим именем — конфликт
                if existing_addr.name != new_p.name:
                    return False, (f"Адрес {new_p.address[:16]}... уже "
                                  f"зарегистрирован как '{existing_addr.name}'")
            self.profiles[new_p.name] = new_p
            self._by_address[new_p.address] = new_p
            self._save()
            return True, "добавлен"

        # Сравниваем свежесть
        if new_p.updated_at > existing.updated_at:
            self.profiles[new_p.name] = new_p
            self._by_address[new_p.address] = new_p
            self._save()
            return True, "обновлён"

        return True, "уже актуален"

    def __len__(self):
        return len(self.profiles)

    def __repr__(self):
        return f"AIXIDManager({len(self.profiles)} profiles)"