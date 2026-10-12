"""
AIX OS — Кошелёк.

Кошелёк = пара ключей (приватный + публичный) + адрес + метаданные.

Приватный ключ хранится в файле кошелька в hex-формате.
Файл: data/wallets/<имя>.wallet.json

⚠️  ВАЖНО: в реальном продукте приватные ключи надо шифровать паролем!
    Здесь — упрощённая версия для MVP.
"""

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.keys import (
    generate_private_key,
    private_key_to_bytes,
    private_key_from_bytes,
    get_public_key_bytes,
    sign,
)
from crypto.address import private_key_to_address, pubkey_to_address
import ecdsa

import config


# =============================================================================
# КОШЕЛЁК
# =============================================================================

@dataclass
class Wallet:
    """Кошелёк AIX."""

    name: str                       # Имя кошелька (для файла)
    address: str                    # AIX-адрес
    public_key: str                 # hex публичного ключа
    private_key: str                # hex приватного ключа (⚠️ в продакшне — шифровать!)
    created_at: float               # когда создан

    # Не храним сам объект ключа — только hex, восстанавливаем при необходимости

    # =========================================================================
    # СОЗДАНИЕ
    # =========================================================================

    @classmethod
    def create(cls, name: str) -> "Wallet":
        """Создать новый кошелёк."""
        sk = generate_private_key()
        addr = private_key_to_address(sk)
        pub = get_public_key_bytes(sk)

        return cls(
            name=name,
            address=addr,
            public_key=pub.hex(),
            private_key=sk.to_string().hex(),
            created_at=time.time(),
        )

    # =========================================================================
    # КЛЮЧИ
    # =========================================================================

    def get_signing_key(self) -> ecdsa.SigningKey:
        """Получить объект приватного ключа для подписи."""
        return private_key_from_bytes(bytes.fromhex(self.private_key))

    def get_public_key_bytes(self) -> bytes:
        """Публичный ключ как байты."""
        return bytes.fromhex(self.public_key)

    # =========================================================================
    # ПОДПИСЬ
    # =========================================================================

    def sign_transaction(self, tx) -> None:
        """Подписать транзакцию этим кошельком."""
        sk = self.get_signing_key()
        tx.sign_transaction(sk)

    # =========================================================================
    # СОХРАНЕНИЕ / ЗАГРУЗКА
    # =========================================================================

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        return cls(**data)

    def save(self, path: Optional[Path] = None) -> Path:
        """Сохранить кошелёк в файл."""
        if path is None:
            path = config.WALLETS_DIR / f"{self.name}.wallet.json"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

        # На Linux/macOS ограничим права доступа
        try:
            os.chmod(path, 0o600)
        except (OSError, NotImplementedError):
            pass  # На Windows не сработает

        return path

    @classmethod
    def load(cls, name: str) -> "Wallet":
        """Загрузить кошелёк по имени."""
        path = config.WALLETS_DIR / f"{name}.wallet.json"
        if not path.exists():
            raise FileNotFoundError(f"Кошелёк '{name}' не найден в {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    @staticmethod
    def list_wallets() -> list[str]:
        """Список всех кошельков в папке."""
        if not config.WALLETS_DIR.exists():
            return []
        return [
            p.stem.replace(".wallet", "")
            for p in config.WALLETS_DIR.glob("*.wallet.json")
        ]

    @staticmethod
    def exists(name: str) -> bool:
        return (config.WALLETS_DIR / f"{name}.wallet.json").exists()

    # =========================================================================
    # ИНФОРМАЦИЯ
    # =========================================================================

    def __repr__(self) -> str:
        return f"Wallet(name='{self.name}', address='{self.address}')"

    def info(self) -> str:
        """Красивая карточка кошелька."""
        return (
            f"📛 Имя:     {self.name}\n"
            f"💼 Адрес:   {self.address}\n"
            f"🔑 Публичный: {self.public_key[:32]}...\n"
            f"📅 Создан:  {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.created_at))}"
        )


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    print("👛 Тестирую кошельки AIX...\n")

    test_name = "_test_wallet_"

    # Удаляем старый тестовый кошелёк
    old_path = config.WALLETS_DIR / f"{test_name}.wallet.json"
    if old_path.exists():
        old_path.unlink()

    # ===== Создание =====
    print("1. Создаю кошелёк...")
    w = Wallet.create(test_name)
    print(w.info())
    print()

    # ===== Сохранение =====
    print("2. Сохраняю в файл...")
    path = w.save()
    print(f"   Файл: {path}\n")

    # ===== Загрузка =====
    print("3. Загружаю из файла...")
    w2 = Wallet.load(test_name)
    print(f"   Адрес совпадает: {w.address == w2.address}")
    print(f"   Приватный ключ совпадает: {w.private_key == w2.private_key}\n")

    # ===== Подпись транзакции через кошелёк =====
    print("4. Подписываю транзакцию через кошелёк...")
    from core.transaction import Transaction

    tx = Transaction(
        sender=w2.address,
        recipient="AIXTMMuuRvfytUWBu8yZfwpKG6y75MBuFpasg",  # какой-то адрес
        amount=100 * config.SATOSHI,
        message="Тест подписи через Wallet",
    )
    w2.sign_transaction(tx)
    ok, msg = tx.is_valid()
    print(f"   Транзакция валидна: {ok} — {msg}\n")

    # ===== Список кошельков =====
    print(f"5. Все кошельки в системе: {Wallet.list_wallets()}\n")

    # Удаляем тестовый кошелёк
    old_path.unlink()
    print("✅ Кошельки работают.")