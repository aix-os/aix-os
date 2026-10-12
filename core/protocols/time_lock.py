"""
AIX OS — Time-Lock Wallets (#1).

Заморозка AIX до определённой даты.

Как работает:
1. Владелец создаёт timelock: "100 AIX до 2027-01-01" (для себя или для другого)
2. Средства замораживаются (available_balance падает)
3. До даты unlock_at средства нельзя достать НИКОМУ — даже владельцу
4. После unlock_at:
   - Если получатель указан — он активирует капсулу
   - Если получатель не указан — владелец сам активирует
5. Если владелец передумал ДО unlock_at — можно отменить (средства возвращаются)

Хранение: data/timelocks.json
"""

import json
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transaction import Transaction
from core.wallet import Wallet
import config


ID_PREFIX = "TL"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


def parse_date(date_str: str) -> float:
    """
    Парсит дату из строки. Форматы:
      YYYY-MM-DD            → 00:00:00 UTC того дня
      YYYY-MM-DD HH:MM      → точное время UTC
      YYYY-MM-DDTHH:MM:SS   → ISO 8601
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    raise ValueError(
        f"Не могу разобрать дату '{date_str}'. "
        f"Форматы: YYYY-MM-DD или 'YYYY-MM-DD HH:MM'"
    )


def format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@dataclass
class TimeLock:
    """Одна капсула времени."""
    id: str
    owner: str                # AIX-адрес владельца (кто заморозил)
    recipient: str            # AIX-адрес получателя или "" (если себе)
    amount: int               # атомарные единицы
    created_at: float
    unlock_at: float          # когда можно активировать
    message: str = ""
    released: bool = False    # уже активирована
    released_by: str = ""
    released_at: float = 0.0
    cancelled: bool = False

    def is_unlockable(self) -> bool:
        """Можно ли активировать (время пришло и не активировано/отменено)."""
        return (not self.released and not self.cancelled
                and time.time() >= self.unlock_at)

    def is_locked(self) -> bool:
        """Всё ещё заблокирована (время не пришло)."""
        return (not self.released and not self.cancelled
                and time.time() < self.unlock_at)

    def is_active(self) -> bool:
        """Живая (не released, не cancelled, не истекла по времени=не активирована)."""
        return not self.released and not self.cancelled

    def status(self) -> str:
        if self.released:
            return "released"
        if self.cancelled:
            return "cancelled"
        if self.is_unlockable():
            return "unlockable"
        return "locked"

    def time_left_seconds(self) -> float:
        return max(0.0, self.unlock_at - time.time())

    def time_left_str(self) -> str:
        secs = int(self.time_left_seconds())
        if secs == 0:
            return "готово к активации"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins, _ = divmod(rem, 60)
        parts = []
        if days: parts.append(f"{days}д")
        if hours: parts.append(f"{hours}ч")
        if mins and not days: parts.append(f"{mins}м")
        return " ".join(parts) if parts else "меньше минуты"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TimeLock":
        return cls(**data)

    def __repr__(self):
        return (f"TimeLock({self.id}, {self.amount/config.SATOSHI:.2f} AIX, "
                f"{self.status()}, {self.time_left_str()})")


class TimeLockManager:
    """Менеджер капсул. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.locks: dict[str, TimeLock] = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("locks", []):
                lock = TimeLock.from_dict(item)
                self.locks[lock.id] = lock
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Не удалось загрузить timelocks: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"locks": [l.to_dict() for l in self.locks.values()]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # СОЗДАНИЕ
    # =========================================================================

    def create(self, owner: str, amount: int, unlock_at: float,
               recipient: str = "", message: str = "",
               blockchain=None) -> TimeLock:
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        if unlock_at <= time.time():
            raise ValueError("Дата разблокировки должна быть в будущем")

        # Проверяем доступный баланс с учётом заморозки
        bc = blockchain or self.blockchain
        if bc is not None:
            full_balance = bc.get_balance(owner)
            locked = self.locked_balance(owner, bc)
            available = full_balance - locked
            if available < amount:
                raise ValueError(
                    f"Недостаточно свободных средств. "
                    f"Доступно: {available/config.SATOSHI:.4f} AIX, "
                    f"нужно: {amount/config.SATOSHI:.4f} AIX. "
                    f"Учтена заморозка: {locked/config.SATOSHI:.4f} AIX"
                )

        # Уникальный id
        for _ in range(10):
            lid = generate_id()
            if lid not in self.locks:
                break
        else:
            raise RuntimeError("Не удалось сгенерировать уникальный ID")

        lock = TimeLock(
            id=lid,
            owner=owner,
            recipient=recipient or "",
            amount=amount,
            created_at=time.time(),
            unlock_at=unlock_at,
            message=message,
        )
        self.locks[lid] = lock
        self._save()
        return lock

    # =========================================================================
    # ПРОСМОТР
    # =========================================================================

    def get(self, lock_id: str) -> Optional[TimeLock]:
        return self.locks.get(lock_id.upper())

    def list_by_owner(self, address: str) -> list[TimeLock]:
        return [l for l in self.locks.values() if l.owner == address]

    def list_by_recipient(self, address: str) -> list[TimeLock]:
        return [l for l in self.locks.values() if l.recipient == address]

    def list_active(self) -> list[TimeLock]:
        return [l for l in self.locks.values() if l.is_active()]

    def locked_balance(self, address: str, blockchain=None) -> int:
        """Сколько AIX заморожено у адреса (в активных timelocks)."""
        return sum(l.amount for l in self.locks.values()
                   if l.owner == address and l.is_active())

    # =========================================================================
    # АКТИВАЦИЯ
    # =========================================================================

    def release(self, lock_id: str, by_address: str, blockchain=None) -> tuple[bool, str]:
        """Активировать капсулу (после unlock_at)."""
        lock = self.get(lock_id)
        if lock is None:
            return False, "Timelock не найден"
        if lock.released:
            return False, "Уже активирована"
        if lock.cancelled:
            return False, "Была отменена"
        if time.time() < lock.unlock_at:
            return False, (f"Ещё рано. Осталось: {lock.time_left_str()} "
                          f"(до {format_time(lock.unlock_at)})")

        # Кто может активировать?
        recipient_addr = lock.recipient or lock.owner
        if by_address not in (lock.owner, recipient_addr):
            return False, "Только владелец или получатель может активировать"

        # Ищем кошелёк владельца для подписи
        sender_wallet = self._find_wallet(lock.owner)
        if sender_wallet is None:
            return False, f"Локальный кошелёк владельца не найден"

        # Создаём транзакцию owner → recipient
        tx = Transaction(
            sender=lock.owner,
            recipient=recipient_addr,
            amount=lock.amount,
            message=lock.message or f"Time-Lock {lock.id} release",
        )
        sender_wallet.sign_transaction(tx)
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Ошибка подписи: {msg}"

        bc = blockchain or self.blockchain
        if bc is not None:
            ok, msg = bc.mempool.add(tx)
            if not ok:
                return False, f"Не добавлено в mempool: {msg}"

        lock.released = True
        lock.released_by = by_address
        lock.released_at = time.time()
        self._save()
        return True, tx.tx_id()

    # =========================================================================
    # ОТМЕНА (только до unlock_at и только владельцем)
    # =========================================================================

    def cancel(self, lock_id: str, by_address: str) -> tuple[bool, str]:
        lock = self.get(lock_id)
        if lock is None:
            return False, "Не найден"
        if lock.released:
            return False, "Уже активирована — нельзя отменить"
        if lock.cancelled:
            return False, "Уже отменена"
        if lock.owner != by_address:
            return False, "Только владелец может отменить"
        if time.time() >= lock.unlock_at:
            return False, "Время пришло — отмена невозможна, только активация"
        lock.cancelled = True
        self._save()
        return True, "OK"

    # =========================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # =========================================================================

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
        return len(self.locks)

    def __repr__(self):
        return f"TimeLockManager({len(self.locks)} locks)"