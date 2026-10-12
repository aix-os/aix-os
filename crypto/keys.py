"""
AIX OS — Ключи и подписи (ECDSA secp256k1).

ПРИВАТНЫЙ ключ — секрет. Никогда никому не показывай.
ПУБЛИЧНЫЙ ключ — можно показывать. Из него делается адрес.
ПОДПИСЬ — доказательство, что транзакцию создал владелец приватного ключа.
"""

import ecdsa
import secrets
from typing import Tuple

from .hash import sha256

# Кривая secp256k1 — стандарт Bitcoin/Ethereum
CURVE = ecdsa.SECP256k1


def generate_private_key() -> ecdsa.SigningKey:
    """
    Генерирует новый приватный ключ.
    Использует криптографически стойкий генератор случайных чисел.
    """
    return ecdsa.SigningKey.generate(curve=CURVE)


def private_key_to_bytes(sk: ecdsa.SigningKey) -> bytes:
    """Приватный ключ → 32 байта."""
    return sk.to_string()


def private_key_from_bytes(data: bytes) -> ecdsa.SigningKey:
    """Восстановление приватного ключа из 32 байт."""
    return ecdsa.SigningKey.from_string(data, curve=CURVE)


def get_public_key_bytes(sk: ecdsa.SigningKey) -> bytes:
    """
    Публичный ключ в сжатом формате (33 байта).
    Начинается с 0x02 или 0x03.
    """
    vk = sk.get_verifying_key()
    return vk.to_string("compressed")


def sign(sk: ecdsa.SigningKey, message: bytes) -> bytes:
    """
    Подписать сообщение приватным ключом.
    Возвращает подпись (обычно ~70–72 байта в DER-формате).
    """
    return sk.sign(message)


def verify(pubkey_bytes: bytes, signature: bytes, message: bytes) -> bool:
    """
    Проверить, что подпись действительно сделана владельцем публичного ключа.
    Возвращает True/False.
    """
    try:
        vk = ecdsa.VerifyingKey.from_string(pubkey_bytes, curve=CURVE)
        return vk.verify(signature, message)
    except ecdsa.BadSignatureError:
        return False
    except Exception:
        return False


# Быстрый тест при запуске файла напрямую
if __name__ == "__main__":
    print("🔐 Генерирую пару ключей...")
    sk = generate_private_key()
    priv_bytes = private_key_to_bytes(sk)
    pub_bytes = get_public_key_bytes(sk)

    print(f"Приватный (hex, НИКОМУ):  {priv_bytes.hex()}")
    print(f"Публичный  (compressed):  {pub_bytes.hex()}")
    print(f"Длина публичного:         {len(pub_bytes)} байт (должно быть 33)")

    # Тест подписи
    message = b"AIX: translate 100 AIX to Alice"
    signature = sign(sk, message)
    print(f"Подпись:                  {signature.hex()[:64]}... ({len(signature)} байт)")

    # Проверка
    is_valid = verify(pub_bytes, signature, message)
    print(f"Проверка подписи:         {'✅ OK' if is_valid else '❌ ПРОВАЛ'}")

    # Проверка на подделке
    is_valid_fake = verify(pub_bytes, signature, b"fake message")
    print(f"Проверка подделки:        {'❌ ПРОБЛЕМА' if is_valid_fake else '✅ Отклонена'}")

    print("✅ Криптография ключей работает.")