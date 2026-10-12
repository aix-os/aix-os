"""
AIX OS — AIX Contacts (#13).

Телефонная книга на блокчейне с privacy-by-design.

Как работает:
1. Владелец регистрирует свой номер: sha256(SALT + normalized_phone)
2. Хеш привязывается к его AIX-адресу
3. Любой может нормализовать номер, захешировать и спросить сеть: «Кто это?»
4. Если адрес найден — можно отправить AIX прямо по номеру

Приватность:
- Номер НИКОГДА не хранится в открытом виде
- Только SHA-256 хеш с солью проекта
- На сервер уходит только хеш
- Даже оператор ноды не может узнать номера в базе

Ограничения:
- Один номер ↔ один адрес
- Один адрес может иметь несколько номеров (например, личный + рабочий)
"""

import hashlib
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

# Соль проекта — одинаковая на всех нодах, нужна чтобы хеши совпадали.
# ВАЖНО: не менять после первого релиза, иначе все хеши станут невалидными.
PHONE_SALT = "AIX-OS-PHONE-v1"

# Минимум/максимум цифр в номере (международный стандарт E.164)
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15

# Максимальная длина метки
LABEL_MAX = 40


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона.
    Убирает всё, кроме цифр. Знак + отбрасывается.
    
    Примеры:
        "+7 999 123-45-67" → "79991234567"
        "8 (999) 1234567"  → "89991234567"
        "+1-555-123-4567"  → "15551234567"
    """
    digits = re.sub(r"\D", "", phone)
    return digits


def validate_phone(phone: str) -> tuple[bool, str]:
    """Проверяет нормализованный номер."""
    digits = normalize_phone(phone)
    if len(digits) < PHONE_MIN_DIGITS:
        return False, f"Слишком короткий номер (минимум {PHONE_MIN_DIGITS} цифр)"
    if len(digits) > PHONE_MAX_DIGITS:
        return False, f"Слишком длинный номер (максимум {PHONE_MAX_DIGITS} цифр)"
    return True, "OK"


def phone_hash(phone: str) -> str:
    """
    Хеш номера телефона с солью проекта.
    Детерминированный — одинаковый на всех нодах.
    """
    digits = normalize_phone(phone)
    combined = f"{PHONE_SALT}:{digits}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# =============================================================================
# КОНТАКТ
# =============================================================================

@dataclass
class Contact:
    """Один контакт — привязка хеша номера к AIX-адресу."""
    phone_hash: str          # sha256(соль + normalized_phone)
    address: str             # AIX-адрес владельца
    label: str = ""          # опциональная метка: "мама", "работа"
    created_at: float = 0.0
    verified: bool = False   # подтверждение через SMS (для будущего)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        return cls(**data)

    def __repr__(self):
        return f"Contact({self.phone_hash[:12]}...→{self.address[:16]}...)"


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class ContactsManager:
    """Менеджер контактов. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        # Два индекса для быстрого поиска:
        self.by_phone: dict[str, Contact] = {}    # phone_hash -> Contact
        self.by_address: dict[str, list] = {}     # address -> [Contact, ...]
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("contacts", []):
                c = Contact.from_dict(item)
                self.by_phone[c.phone_hash] = c
                self.by_address.setdefault(c.address, []).append(c)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить контакты: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            all_contacts = list(self.by_phone.values())
            json.dump(
                {"contacts": [c.to_dict() for c in all_contacts]},
                f, ensure_ascii=False, indent=2,
            )
        tmp.replace(self.storage_path)

    # =========================================================================
    # РЕГИСТРАЦИЯ
    # =========================================================================

    def register(self, address: str, phone: str,
                 label: str = "") -> tuple[bool, str, Optional[Contact]]:
        """
        Привязать номер телефона к AIX-адресу.
        Возвращает (успех, сообщение, контакт).
        """
        if not is_valid_address(address):
            return False, "Невалидный AIX-адрес", None

        ok, msg = validate_phone(phone)
        if not ok:
            return False, msg, None

        if label and len(label) > LABEL_MAX:
            return False, f"Метка слишком длинная (макс {LABEL_MAX})", None

        h = phone_hash(phone)
        existing = self.by_phone.get(h)
        if existing is not None:
            if existing.address == address:
                return False, "Этот номер уже привязан к вашему адресу", None
            return False, ("Номер уже привязан к другому AIX-адресу. "
                          "Если это ошибка — свяжитесь с владельцем."), None

        contact = Contact(
            phone_hash=h,
            address=address,
            label=label,
            created_at=time.time(),
        )
        self.by_phone[h] = contact
        self.by_address.setdefault(address, []).append(contact)
        self._save()
        return True, "OK", contact

    # =========================================================================
    # ПОИСК
    # =========================================================================

    def find_by_phone(self, phone: str) -> Optional[Contact]:
        """Найти контакт по номеру. Возвращает Contact или None."""
        h = phone_hash(phone)
        return self.by_phone.get(h)

    def find_by_address(self, address: str) -> list:
        """Все контакты адреса."""
        return list(self.by_address.get(address, []))

    def count_for_address(self, address: str) -> int:
        return len(self.by_address.get(address, []))

    # =========================================================================
    # УДАЛЕНИЕ
    # =========================================================================

    def unregister(self, address: str, phone: str) -> tuple[bool, str]:
        """Отвязать номер от адреса. Только владелец может."""
        h = phone_hash(phone)
        existing = self.by_phone.get(h)
        if existing is None:
            return False, "Номер не найден в базе"
        if existing.address != address:
            return False, "Этот номер принадлежит другому адресу"

        del self.by_phone[h]
        if address in self.by_address:
            self.by_address[address] = [
                c for c in self.by_address[address] if c.phone_hash != h
            ]
            if not self.by_address[address]:
                del self.by_address[address]
        self._save()
        return True, "OK"

    # =========================================================================
    # СИНХРОНИЗАЦИЯ
    # =========================================================================

    def export_all(self) -> list:
        """Для state sync — отдаём все контакты."""
        return [c.to_dict() for c in self.by_phone.values()]

    def import_contact(self, data: dict) -> tuple[bool, str]:
        """
        Merge одного контакта.
        Конфликт: если хеш уже занят другим адресом — пропускаем.
        """
        try:
            new_c = Contact.from_dict(data)
        except Exception as e:
            return False, f"Ошибка парсинга: {e}"

        existing = self.by_phone.get(new_c.phone_hash)
        if existing is not None:
            if existing.address == new_c.address:
                # Тот же контакт — возможно, обновилась метка
                if new_c.label != existing.label:
                    existing.label = new_c.label
                    self._save()
                    return True, "обновлён"
                return True, "уже есть"
            # Конфликт — хеш занят другим адресом
            return False, "конфликт (номер занят)"

        self.by_phone[new_c.phone_hash] = new_c
        self.by_address.setdefault(new_c.address, []).append(new_c)
        self._save()
        return True, "добавлен"

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def __len__(self):
        return len(self.by_phone)

    def unique_addresses(self) -> int:
        return len(self.by_address)

    def __repr__(self):
        return (f"ContactsManager({len(self.by_phone)} contacts, "
                f"{len(self.by_address)} addresses)")


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    print("📇 Тестирую AIX Contacts...\n")

    # Нормализация
    print("1. Нормализация номеров:")
    for raw in ["+7 999 123-45-67", "8 (999) 1234567", "+1-555-123-4567"]:
        n = normalize_phone(raw)
        h = phone_hash(raw)
        print(f"   '{raw}' → '{n}'")
        print(f"      hash: {h[:32]}...")
    print()

    # Валидация
    print("2. Валидация:")
    for phone in ["123", "79991234567", "1" * 20]:
        ok, msg = validate_phone(phone)
        print(f"   '{phone}': {ok} — {msg}")
    print()

    # Менеджер
    import tempfile
    tmp_path = Path(tempfile.gettempdir()) / "test_contacts.json"
    if tmp_path.exists():
        tmp_path.unlink()

    mgr = ContactsManager(tmp_path)

    addr_alice = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
    addr_bob = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"

    # Регистрация
    print("3. Регистрация:")
    ok, msg, c = mgr.register(addr_alice, "+79991234567", "Алиса личный")
    print(f"   Alice: {ok} — {msg}")
    ok, msg, c = mgr.register(addr_alice, "+79997654321", "Алиса работа")
    print(f"   Alice (2й): {ok} — {msg}")
    ok, msg, c = mgr.register(addr_bob, "+15551234567", "Боб")
    print(f"   Bob: {ok} — {msg}")
    print()

    # Конфликт
    print("4. Конфликт (тот же номер, другой адрес):")
    ok, msg, c = mgr.register(addr_bob, "+79991234567")
    print(f"   {ok} — {msg}")
    print()

    # Поиск
    print("5. Поиск по номеру:")
    c = mgr.find_by_phone("+7 999 123-45-67")
    print(f"   '+7 999 123-45-67' → {c.address if c else 'не найден'}")
    c = mgr.find_by_phone("+7 999 000-00-00")
    print(f"   '+7 999 000-00-00' → {c.address if c else 'не найден'}")
    print()

    # Список контактов
    print("6. Контакты Алисы:")
    for c in mgr.find_by_address(addr_alice):
        print(f"   • {c.label} ({c.phone_hash[:12]}...)")
    print()

    # Удаление
    print("7. Удаление:")
    ok, msg = mgr.unregister(addr_alice, "+79997654321")
    print(f"   Удалить 2й: {ok} — {msg}")
    print(f"   Осталось у Алисы: {mgr.count_for_address(addr_alice)}")
    print()

    # Статистика
    print(f"8. Итого: {mgr}")
    print(f"   Уникальных адресов: {mgr.unique_addresses()}")

    tmp_path.unlink()
    print("\n✅ AIX Contacts работает.")