"""
AIX OS — P2P Обмен (Fiat Gateway).

Позволяет пользователям обменивать AIX на рубли напрямую друг с другом.
Эскроу-механизм: AIX продавца блокируются на системном адресе P2P-ESCROW.
Покупатель переводит рубли напрямую продавцу (карта/СБП).
Продавец подтверждает получение — AIX уходят покупателю.

Статусы ордера:
    open       — продавец выставил, AIX заблокированы, ждём покупателя
    accepted   — покупатель принял, зафиксирована сумма сделки
    paid       — покупатель подтвердил, что перевёл рубли
    completed  — продавец подтвердил получение, AIX ушли покупателю
    cancelled  — отменён продавцом, AIX вернулись
    disputed   — открыт спор, ждём арбитра

Хранение: data/p2p_{port}.json
"""

import json
import random
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transaction import Transaction
from crypto.address import is_valid_address
import config


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

ID_PREFIX = "P2P"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Системный адрес-эскроу (как COINBASE, LOTTERY, POC-POOL)
SYSTEM_ESCROW_ADDRESS = "P2P-ESCROW"

STATUSES = ("open", "accepted", "paid", "completed", "cancelled", "disputed")

PAYMENT_METHODS = {
    "card": "Банковская карта",
    "sbp": "СБП",
    "cash": "Наличные",
}


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


# =============================================================================
# ОРДЕР
# =============================================================================

@dataclass
class P2POrder:
    """Один P2P-ордер на продажу AIX за рубли."""
    id: str
    seller: str
    amount_raw: int              # сколько AIX заблокировано (в сатоши)
    price_rub_per_aix: float     # цена за 1 AIX в рублях
    min_amount_raw: int          # минимальная сумма сделки
    max_amount_raw: int          # максимальная сумма сделки
    payment_method: str          # card / sbp / cash
    status: str = "open"
    buyer: str = ""
    deal_amount_raw: int = 0     # сколько AIX покупается в этой сделке
    escrow_tx_id: str = ""       # TX, которой AIX ушли в P2P-ESCROW
    created_at: float = 0.0
    updated_at: float = 0.0
    chat: list = field(default_factory=list)  # [{from, text, ts}]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "P2POrder":
        return cls(**data)

    def amount_aix(self) -> float:
        return self.amount_raw / config.SATOSHI

    def deal_amount_aix(self) -> float:
        return self.deal_amount_raw / config.SATOSHI

    def total_rub(self) -> float:
        return self.deal_amount_aix() * self.price_rub_per_aix

    def __repr__(self):
        return f"P2POrder({self.id}, {self.amount_aix():.2f} AIX, {self.status})"


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class P2PManager:
    """Менеджер P2P-ордеров. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.orders: dict[str, P2POrder] = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("orders", []):
                o = P2POrder.from_dict(item)
                self.orders[o.id] = o
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить P2P: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "orders": [o.to_dict() for o in self.orders.values()],
            }, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # СОЗДАНИЕ
    # =========================================================================

    def create_order(self, seller: str, amount_raw: int,
                     price_rub_per_aix: float,
                     min_amount_raw: int, max_amount_raw: int,
                     payment_method: str, escrow_tx_id: str) -> tuple:
        if not is_valid_address(seller):
            return False, "Невалидный адрес продавца"
        if amount_raw <= 0:
            return False, "Сумма должна быть положительной"
        if price_rub_per_aix <= 0:
            return False, "Цена должна быть положительной"
        if min_amount_raw <= 0 or max_amount_raw < min_amount_raw:
            return False, "Неверный диапазон сумм"
        if max_amount_raw > amount_raw:
            return False, "Максимум не может быть больше суммы"
        if payment_method not in PAYMENT_METHODS:
            return False, f"Неизвестный способ оплаты. Доступно: {', '.join(PAYMENT_METHODS)}"
        if not escrow_tx_id:
            return False, "Нужен tx_id транзакции seller → P2P-ESCROW"

        for _ in range(10):
            oid = generate_id()
            if oid not in self.orders:
                break
        else:
            return False, "Не удалось сгенерировать ID"

        now = time.time()
        order = P2POrder(
            id=oid,
            seller=seller,
            amount_raw=amount_raw,
            price_rub_per_aix=price_rub_per_aix,
            min_amount_raw=min_amount_raw,
            max_amount_raw=max_amount_raw,
            payment_method=payment_method,
            status="open",
            escrow_tx_id=escrow_tx_id,
            created_at=now,
            updated_at=now,
        )
        self.orders[oid] = order
        self._save()
        return True, oid

    # =========================================================================
    # ДЕЙСТВИЯ
    # =========================================================================

    def accept_order(self, order_id: str, buyer: str,
                     deal_amount_raw: int) -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if o.status != "open":
            return False, f"Ордер в статусе {o.status}"
        if not is_valid_address(buyer):
            return False, "Невалидный адрес покупателя"
        if buyer == o.seller:
            return False, "Нельзя торговать с самим собой"
        if deal_amount_raw < o.min_amount_raw or deal_amount_raw > o.max_amount_raw:
            return False, (
                f"Сумма вне диапазона "
                f"{o.min_amount_raw/config.SATOSHI:.2f} - "
                f"{o.max_amount_raw/config.SATOSHI:.2f} AIX"
            )

        o.buyer = buyer
        o.deal_amount_raw = deal_amount_raw
        o.status = "accepted"
        o.updated_at = time.time()
        self._save()
        return True, "OK"

    def confirm_paid(self, order_id: str, buyer: str) -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if o.status != "accepted":
            return False, f"Ордер в статусе {o.status}"
        if o.buyer != buyer:
            return False, "Только покупатель может подтвердить оплату"

        o.status = "paid"
        o.updated_at = time.time()
        self._save()
        return True, "OK"

    def release(self, order_id: str, seller: str, blockchain=None) -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if o.status != "paid":
            return False, f"Ордер в статусе {o.status}"
        if o.seller != seller:
            return False, "Только продавец может подтвердить получение фиата"
        if not o.buyer:
            return False, "Нет покупателя"

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна"

        tx = Transaction(
            sender=SYSTEM_ESCROW_ADDRESS,
            recipient=o.buyer,
            amount=o.deal_amount_raw,
            message=f"🔄 P2P release {o.id}",
        )
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}"
        ok, msg = bc.mempool.add(tx)
        if not ok:
            return False, f"Не добавлено в mempool: {msg}"

        o.status = "completed"
        o.updated_at = time.time()
        self._save()
        return True, tx.tx_id()

    def cancel(self, order_id: str, seller: str, blockchain=None) -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if o.seller != seller:
            return False, "Только продавец может отменить"
        if o.status not in ("open", "accepted"):
            return False, f"Нельзя отменить в статусе {o.status}"

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна"

        tx = Transaction(
            sender=SYSTEM_ESCROW_ADDRESS,
            recipient=o.seller,
            amount=o.amount_raw,
            message=f"↩️ P2P cancel {o.id}",
        )
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}"
        ok, msg = bc.mempool.add(tx)
        if not ok:
            return False, f"Не добавлено в mempool: {msg}"

        o.status = "cancelled"
        o.updated_at = time.time()
        self._save()
        return True, tx.tx_id()

    def dispute(self, order_id: str, by: str, reason: str = "") -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if o.status not in ("accepted", "paid"):
            return False, f"Нельзя открыть спор в статусе {o.status}"
        if by not in (o.seller, o.buyer):
            return False, "Только участник сделки может открыть спор"

        o.status = "disputed"
        o.chat.append({
            "from": by,
            "text": f"⚠️ СПОР: {reason}",
            "ts": time.time(),
        })
        o.updated_at = time.time()
        self._save()
        return True, "OK"

    def add_chat_message(self, order_id: str, from_addr: str, text: str) -> tuple:
        o = self.get(order_id)
        if o is None:
            return False, "Ордер не найден"
        if from_addr not in (o.seller, o.buyer) and from_addr != "ARBITER":
            return False, "Только участник сделки может писать"
        if not text or len(text) > 500:
            return False, "Текст обязателен (макс 500 символов)"

        o.chat.append({
            "from": from_addr,
            "text": text.strip(),
            "ts": time.time(),
        })
        o.updated_at = time.time()
        self._save()
        return True, "OK"

    # =========================================================================
    # ПРОСМОТР
    # =========================================================================

    def get(self, order_id: str) -> Optional[P2POrder]:
        return self.orders.get(order_id.upper())

    def list_open(self) -> list:
        return sorted(
            [o for o in self.orders.values() if o.status == "open"],
            key=lambda o: o.created_at, reverse=True,
        )

    def list_by_seller(self, address: str) -> list:
        return sorted(
            [o for o in self.orders.values() if o.seller == address],
            key=lambda o: o.created_at, reverse=True,
        )

    def list_by_buyer(self, address: str) -> list:
        return sorted(
            [o for o in self.orders.values() if o.buyer == address],
            key=lambda o: o.created_at, reverse=True,
        )

    def list_all(self, limit: int = 100) -> list:
        return sorted(
            self.orders.values(),
            key=lambda o: o.created_at, reverse=True,
        )[:limit]

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def stats(self) -> dict:
        by_status = {}
        for o in self.orders.values():
            by_status[o.status] = by_status.get(o.status, 0) + 1
        total_volume_rub = sum(
            o.total_rub() for o in self.orders.values()
            if o.status == "completed"
        )
        return {
            "total_orders": len(self.orders),
            "by_status": by_status,
            "total_volume_rub": total_volume_rub,
            "payment_methods": PAYMENT_METHODS,
        }

    def __len__(self):
        return len(self.orders)

    def __repr__(self):
        return f"P2PManager({len(self.orders)} orders)"