"""
AIX OS — Gift-Link (#6).

Отправка AIX человеку БЕЗ кошелька.

Как работает:
1. Отправитель создаёт ссылку с уникальным кодом (AIX-XXXX-XXXX)
2. Средства резервируются (available_balance уменьшается)
3. Получатель активирует код → сервер создаёт блокчейн-транзакцию
4. Если не активировал за TTL дней → средства размораживаются

Хранение: data/gifts.json
"""

import json
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transaction import Transaction
from core.wallet import Wallet
import config


CODE_PREFIX = "AIX"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_TTL_DAYS = 30


def generate_code() -> str:
    """Читаемый код вида AIX-7K9M-2PQ4."""
    part1 = "".join(random.choices(CODE_ALPHABET, k=4))
    part2 = "".join(random.choices(CODE_ALPHABET, k=4))
    return f"{CODE_PREFIX}-{part1}-{part2}"


@dataclass
class GiftLink:
    """Одна gift-ссылка."""
    code: str
    sender: str
    amount: int
    created_at: float
    expires_at: float
    message: str = ""
    claimed: bool = False
    claimed_by: str = ""
    claimed_at: float = 0.0
    cancelled: bool = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_active(self) -> bool:
        return not self.claimed and not self.cancelled and not self.is_expired()

    def status(self) -> str:
        if self.claimed:
            return "claimed"
        if self.cancelled:
            return "cancelled"
        if self.is_expired():
            return "expired"
        return "active"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GiftLink":
        return cls(**data)

    def __repr__(self):
        return f"GiftLink({self.code}, {self.amount/config.SATOSHI:.2f} AIX, {self.status()})"


class GiftLinkManager:
    """Менеджер gift-ссылок. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.links: dict[str, GiftLink] = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("links", []):
                link = GiftLink.from_dict(item)
                self.links[link.code] = link
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить gift-ссылки: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"links": [l.to_dict() for l in self.links.values()]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    def create(self, sender: str, amount: int,
               ttl_days: int = DEFAULT_TTL_DAYS,
               message: str = "") -> GiftLink:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")

        if self.blockchain is not None:
            full_balance = self.blockchain.get_balance(sender)
            locked = self.locked_balance(sender)
            available = full_balance - locked
            if available < amount:
                raise ValueError(
                    f"Недостаточно свободных средств. "
                    f"Доступно: {available/config.SATOSHI:.4f} AIX, "
                    f"нужно: {amount/config.SATOSHI:.4f} AIX "
                    f"(заморожено: {locked/config.SATOSHI:.4f})"
                )

        for _ in range(10):
            code = generate_code()
            if code not in self.links:
                break
        else:
            raise RuntimeError("Не удалось сгенерировать уникальный код")

        now = time.time()
        link = GiftLink(
            code=code,
            sender=sender,
            amount=amount,
            created_at=now,
            expires_at=now + ttl_days * 86400,
            message=message,
        )
        self.links[code] = link
        self._save()
        return link

    def get(self, code: str) -> Optional[GiftLink]:
        return self.links.get(code.upper())

    def list_by_sender(self, address: str) -> list:
        return [l for l in self.links.values() if l.sender == address]

    def list_active(self) -> list:
        return [l for l in self.links.values() if l.is_active()]

    def locked_balance(self, address: str) -> int:
        return sum(l.amount for l in self.links.values()
                   if l.sender == address and l.is_active())

    def claim(self, code: str, recipient: str) -> tuple:
        link = self.get(code)
        if link is None:
            return False, "Gift-ссылка не найдена"
        if link.claimed:
            return False, f"Уже активирована ({link.claimed_by[:20]}...)"
        if link.cancelled:
            return False, "Ссылка была отменена отправителем"
        if link.is_expired():
            return False, "Срок действия ссылки истёк"

        # ESCROW: переводим GIFT-ESCROW → recipient (системный sender)
        tx = Transaction(
            sender="GIFT-ESCROW",
            recipient=recipient,
            amount=link.amount,
            message=link.message or f"Gift-Link {link.code}",
        )
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Ошибка валидации: {msg}"

        if self.blockchain is not None:
            ok, msg = self.blockchain.mempool.add(tx)
            if not ok:
                return False, f"Не добавлено в mempool: {msg}"
            try:
                self.blockchain.mine_block(recipient)
            except Exception:
                pass

        link.claimed = True
        link.claimed_by = recipient
        link.claimed_at = time.time()
        self._save()
        return True, tx.tx_id()

    def cancel(self, code: str, sender: str) -> tuple:
        link = self.get(code)
        if link is None:
            return False, "Не найдена"
        if link.claimed:
            return False, "Уже активирована — нельзя отменить"
        if link.sender != sender:
            return False, "Только отправитель может отменить"
        if link.cancelled:
            return False, "Уже отменена"
        
        # ESCROW: возвращаем GIFT-ESCROW → sender
        if self.blockchain is not None:
            tx = Transaction(
                sender="GIFT-ESCROW",
                recipient=link.sender,
                amount=link.amount,
                message=f"Gift cancel {link.code}",
            )
            ok, msg = tx.is_valid()
            if ok:
                blockchain_ok, _ = self.blockchain.mempool.add(tx)
                if blockchain_ok:
                    try:
                        self.blockchain.mine_block(link.sender)
                    except Exception:
                        pass
        
        link.cancelled = True
        self._save()
        return True, "OK"

    def cleanup_expired(self) -> int:
        expired = [c for c, l in self.links.items()
                   if l.is_expired() and not l.claimed]
        for c in expired:
            del self.links[c]
        if expired:
            self._save()
        return len(expired)

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
        return len(self.links)

    def __repr__(self):
        return f"GiftLinkManager({len(self.links)} links)"