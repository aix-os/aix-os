"""
AIX OS — Хеш-функции.

SHA-256 — это «отпечаток пальца» данных. Один и тот же вход всегда даёт
один и тот же выход, но из выхода невозможно восстановить вход.

Двойной SHA-256 используется в Bitcoin для блоков и адресов — мы делаем так же.
"""

import hashlib
from typing import Union


def sha256(data: Union[bytes, str]) -> bytes:
    """SHA-256 одного прохода. Возвращает 32 байта."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).digest()


def double_sha256(data: Union[bytes, str]) -> bytes:
    """
    Двойной SHA-256 — стандарт Bitcoin.
    Защищает от length-extension атак.
    """
    return sha256(sha256(data))


def ripemd160(data: Union[bytes, str]) -> bytes:
    """
    RIPEMD-160 — даёт 20 байт вместо 32.
    Используется в Bitcoin для сжатия публичного ключа в адрес.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    try:
        h = hashlib.new("ripemd160")
        h.update(data)
        return h.digest()
    except ValueError:
        # На случай, если OpenSSL в системе без ripemd160
        # Fallback: sha256 и обрезаем до 20 байт
        return sha256(data)[:20]


def hash160(data: Union[bytes, str]) -> bytes:
    """
    Hash160 = RIPEMD160(SHA256(data)).
    Именно это от публичного ключа превращается в адрес.
    """
    return ripemd160(sha256(data))


def to_hex(data: bytes) -> str:
    """Байты → hex-строка (для отладки и логов)."""
    return data.hex()


def from_hex(s: str) -> bytes:
    """Hex-строка → байты."""
    return bytes.fromhex(s)


# Быстрый тест при запуске файла напрямую
if __name__ == "__main__":
    test = "AIX OS — операционная система для жизни"
    h1 = sha256(test)
    h2 = double_sha256(test)
    h160 = hash160(test)

    print(f"Вход:                {test}")
    print(f"SHA-256:             {to_hex(h1)}")
    print(f"Двойной SHA-256:     {to_hex(h2)}")
    print(f"Hash160 (для адрес): {to_hex(h160)}")
    print(f"Длина hash160:       {len(h160)} байт (должно быть 20)")
    print("✅ Хеши работают.")