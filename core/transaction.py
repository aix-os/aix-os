"""
AIX OS — Транзакция.

Особые sender'ы:
- "COINBASE"  — награда майнеру за блок
- "LOTTERY"   — приз счастливого блока
- "POC-POOL"  — выплата награды за вклад

Особые recipient'ы:
- "BURN"      — сжигание монет
- "POC-POOL"  — донат в фонд PoC
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.hash import sha256
from crypto.keys import sign, verify
from crypto.address import is_valid_address, pubkey_to_address
import ecdsa


SYSTEM_SENDERS = {"COINBASE", "LOTTERY", "POC-POOL"}
SYSTEM_RECIPIENTS = {"BURN", "POC-POOL"}
MIN_FEE = 0


@dataclass
class Transaction:
    """Одна транзакция AIX."""

    sender: str
    recipient: str
    amount: int
    timestamp: float = field(default_factory=time.time)
    fee: int = 0
    public_key: str = ""
    signature: str = ""
    message: str = ""

    def to_signing_payload(self) -> bytes:
        data = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "fee": self.fee,
            "message": self.message,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return canonical.encode("utf-8")

    def tx_id(self) -> str:
        return sha256(self.to_signing_payload()).hex()

    def sign_transaction(self, private_key: ecdsa.SigningKey) -> None:
        payload = self.to_signing_payload()
        signature = sign(private_key, payload)
        from crypto.keys import get_public_key_bytes
        self.public_key = get_public_key_bytes(private_key).hex()
        self.signature = signature.hex()

    def is_valid(self) -> tuple:
        # Системные sender'ы
        if self.sender in SYSTEM_SENDERS:
            if self.amount <= 0:
                return False, f"{self.sender}-сумма должна быть положительной"
            # Получатель может быть AIX-адресом или системным (BURN)
            if self.recipient not in SYSTEM_RECIPIENTS:
                if not is_valid_address(self.recipient):
                    return False, "Невалидный адрес получателя"
            return True, f"{self.sender} OK"

        # Обычная транзакция
        if not is_valid_address(self.sender):
            return False, "Невалидный адрес отправителя"

        if self.recipient in SYSTEM_RECIPIENTS:
            pass
        elif not is_valid_address(self.recipient):
            return False, "Невалидный адрес получателя"

        if self.amount <= 0:
            return False, "Сумма должна быть положительной"
        if self.sender == self.recipient:
            return False, "Нельзя переводить самому себе"
        if not self.signature or not self.public_key:
            return False, "Нет подписи или публичного ключа"

        try:
            pub_bytes = bytes.fromhex(self.public_key)
        except ValueError:
            return False, "Публичный ключ не в hex-формате"

        derived_address = pubkey_to_address(pub_bytes)
        if derived_address != self.sender:
            return False, "Публичный ключ не соответствует адресу отправителя"

        try:
            signature = bytes.fromhex(self.signature)
        except ValueError:
            return False, "Подпись не в hex-формате"

        payload = self.to_signing_payload()
        if not verify(pub_bytes, signature, payload):
            return False, "Подпись недействительна"

        return True, "OK"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def create_coinbase(cls, recipient: str, amount: int, message: str = "") -> "Transaction":
        return cls(sender="COINBASE", recipient=recipient, amount=amount,
                   fee=0, message=message or "AIX OS — майнинг награда")

    @classmethod
    def create_lottery(cls, recipient: str, amount: int, message: str = "") -> "Transaction":
        return cls(sender="LOTTERY", recipient=recipient, amount=amount,
                   fee=0, message=message or "🎰 AIX Lottery")

    @classmethod
    def create_poc_payout(cls, recipient: str, amount: int, message: str = "") -> "Transaction":
        return cls(sender="POC-POOL", recipient=recipient, amount=amount,
                   fee=0, message=message or "🧬 PoC reward")

    def is_burn(self) -> bool:
        return self.recipient == "BURN"

    def is_poc_donation(self) -> bool:
        return self.recipient == "POC-POOL"

    def __repr__(self) -> str:
        return f"Transaction({self.sender[:12]}... → {self.recipient[:12]}..., {self.amount})"