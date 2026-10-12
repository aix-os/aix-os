"""
AIX OS — Адреса.

Формат адреса AIX:
    AIX + Base58Check( version_byte + hash160(pubkey) )

Как это работает:
1. Берём публичный ключ (33 байта).
2. Считаем от него hash160 = RIPEMD160(SHA256(pubkey)) → 20 байт.
3. Добавляем version byte (0x41 = "A" для AIX).
4. Считаем контрольную сумму: первые 4 байта двойного SHA-256.
5. Кодируем всё в Base58.
6. Добавляем человекочитаемый префикс "AIX".

Итог: AIX7fP3kLm9Qx2RtYvN8wZs4 — коротко, красиво, с защитой от опечаток.
"""

import base58
from typing import Optional

from .hash import hash160, double_sha256
from .keys import get_public_key_bytes
import ecdsa

# Версия адреса (0x41 = 65 = буква "A", как намёк на AIX)
VERSION_BYTE = 0x41
PREFIX = "AIX"

# Длина базовой части адреса (без префикса "AIX")
# 1 байт версии + 20 байт hash160 + 4 байта checksum = 25 байт
ADDRESS_PAYLOAD_LEN = 25


# =============================================================================
# BASE58CHECK
# =============================================================================

def base58check_encode(payload: bytes) -> str:
    """
    Кодирует payload в Base58Check-строку.
    Base58Check = base58(payload + checksum)
    """
    checksum = double_sha256(payload)[:4]
    return base58.b58encode(payload + checksum).decode("ascii")


def base58check_decode(encoded: str) -> Optional[bytes]:
    """
    Декодирует Base58Check. Возвращает payload без checksum или None при ошибке.
    """
    try:
        decoded = base58.b58decode(encoded)
    except Exception:
        return None

    if len(decoded) < 5:
        return None

    payload = decoded[:-4]
    checksum = decoded[-4:]
    expected = double_sha256(payload)[:4]

    if checksum != expected:
        return None
    return payload


# =============================================================================
# ГЕНЕРАЦИЯ АДРЕСА
# =============================================================================

def pubkey_to_address(pubkey_bytes: bytes) -> str:
    """
    Публичный ключ → красивый AIX-адрес.
    """
    h160 = hash160(pubkey_bytes)
    payload = bytes([VERSION_BYTE]) + h160
    encoded = base58check_encode(payload)
    return f"{PREFIX}{encoded}"


def address_to_hash160(address: str) -> Optional[bytes]:
    """
    AIX-адрес → hash160 (20 байт). Нужно для проверки и переводов.
    Возвращает None, если адрес невалидный.
    """
    if not address.startswith(PREFIX):
        return None

    encoded = address[len(PREFIX):]
    payload = base58check_decode(encoded)

    if payload is None or len(payload) != 21:
        return None
    if payload[0] != VERSION_BYTE:
        return None

    return payload[1:]


def is_valid_address(address: str) -> bool:
    """Проверяет, является ли строка корректным AIX-адресом."""
    return address_to_hash160(address) is not None


def private_key_to_address(sk: ecdsa.SigningKey) -> str:
    """Сразу приватный ключ → адрес (удобно для CLI)."""
    pub_bytes = get_public_key_bytes(sk)
    return pubkey_to_address(pub_bytes)


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    from .keys import generate_private_key

    print("🎨 Генерирую первый AIX-адрес...")
    print()

    for i in range(3):
        sk = generate_private_key()
        pub = get_public_key_bytes(sk)
        addr = pubkey_to_address(pub)

        print(f"#{i + 1}")
        print(f"  Приватный: {sk.to_string().hex()[:16]}...")
        print(f"  Публичный: {pub.hex()[:16]}...")
        print(f"  Адрес:     {addr}")
        print(f"  Длина:     {len(addr)} символов")
        print(f"  Валиден:   {'✅' if is_valid_address(addr) else '❌'}")
        print()

    # Проверка на битый адрес
    bad = "AIX0000000000000000000000000000000000"
    print(f"Проверка фейкового адреса '{bad}':")
    print(f"  Валиден:   {'❌ ПРОБЛЕМА' if is_valid_address(bad) else '✅ Отклонён корректно'}")
    print()
    print("✅ Генерация адресов AIX работает.")