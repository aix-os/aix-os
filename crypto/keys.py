"""
AIX OS — Ключи и подписи (ECDSA secp256k1).

ПРИВАТНЫЙ ключ — секрет. Никогда никому не показывай.
ПУБЛИЧНЫЙ ключ — можно показывать. Из него делается адрес.
ПОДПИСЬ — доказательство, что транзакцию создал владелец приватного ключа.

ВАЖНО (2026-10-13):
- Хеш для подписи: SHA256 (явно). Раньше был дефолтный SHA1.
- Формат подписи: DER (sigencode_der / sigdecode_der).
  Совпадает с Dart/Flutter-кошельком и стандартом Bitcoin/SSH.
"""

import hashlib

import ecdsa
from ecdsa.util import sigencode_der, sigdecode_der

from .hash import sha256

# Кривая secp256k1 — стандарт Bitcoin/Ethereum
CURVE = ecdsa.SECP256k1

# Хеш для подписи. Менять нельзя — сломает совместимость с Flutter.
SIGN_HASHFUNC = hashlib.sha256


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

    - hashfunc=sha256 — явно (совместимость с Dart).
    - sigencode=sigencode_der — формат подписи DER (SEQUENCE из двух INTEGER).
    """
    return sk.sign(
        message,
        hashfunc=SIGN_HASHFUNC,
        sigencode=sigencode_der,
    )


def verify(pubkey_bytes: bytes, signature: bytes, message: bytes) -> bool:
    """
    Проверить, что подпись действительно сделана владельцем публичного ключа.

    - hashfunc=sha256 — тот же, что в sign.
    - sigdecode=sigdecode_der — читаем DER-подпись.
    """
    try:
        vk = ecdsa.VerifyingKey.from_string(pubkey_bytes, curve=CURVE)
        return vk.verify(
            signature,
            message,
            hashfunc=SIGN_HASHFUNC,
            sigdecode=sigdecode_der,
        )
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
    print(f"Подпись:                  {signature.hex()[:64]}... ({len(signature)} байт DER)")

    # Проверка
    is_valid = verify(pub_bytes, signature, message)
    print(f"Проверка подписи:         {'✅ OK' if is_valid else '❌ ПРОВАЛ'}")

    # Проверка на подделке
    is_valid_fake = verify(pub_bytes, signature, b"fake message")
    print(f"Проверка подделки:        {'❌ ПРОБЛЕМА' if is_valid_fake else '✅ Отклонена'}")

    print("✅ Криптография ключей работает (SHA256 + DER).")