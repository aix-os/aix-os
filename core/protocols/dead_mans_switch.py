"""
AIX OS — Dead Man's Switch (#2).

Наследие на блокчейне. Если владелец не подтверждает активность N месяцев —
средства автоматически уходят наследникам.

Хранение: data/inheritance.json

ВАЖНО: При trigger передаётся available_balance (без заморозки в gift/timelock),
чтобы не украсть замороженные средства.
"""

import json
import random
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.transaction import Transaction
from core.wallet import Wallet
from crypto.address import is_valid_address
import config


ID_PREFIX = "DMS"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

MIN_TIMEOUT_DAYS = 30
DEFAULT_TIMEOUT_DAYS = 365
MAX_HEIRS = 10


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


@dataclass
class Heir:
    """Один наследник с долей."""
    address: str
    share_percent: float
    name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Heir":
        return cls(**data)


@dataclass
class Inheritance:
    """Один switch."""
    id: str
    owner: str
    heirs: list
    timeout_days: int
    created_at: float
    last_checkin: float
    triggered: bool = False
    triggered_by: str = ""
    triggered_at: float = 0.0
    cancelled: bool = False
    note: str = ""

    def time_since_checkin(self) -> float:
        return time.time() - self.last_checkin

    def seconds_until_trigger(self) -> float:
        timeout_sec = self.timeout_days * 86400
        return max(0.0, timeout_sec - self.time_since_checkin())

    def is_triggerable(self) -> bool:
        return (not self.triggered and not self.cancelled
                and self.time_since_checkin() >= self.timeout_days * 86400)

    def is_active(self) -> bool:
        return not self.triggered and not self.cancelled

    def status(self) -> str:
        if self.triggered:
            return "triggered"
        if self.cancelled:
            return "cancelled"
        if self.is_triggerable():
            return "triggerable"
        return "active"

    def time_left_str(self) -> str:
        secs = int(self.seconds_until_trigger())
        if secs == 0:
            return "готов к активации"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        if days:
            return f"{days}д {hours}ч"
        mins, _ = divmod(rem, 60)
        if hours:
            return f"{hours}ч {mins}м"
        return f"{mins}м"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner": self.owner,
            "heirs": [h.to_dict() for h in self.heirs],
            "timeout_days": self.timeout_days,
            "created_at": self.created_at,
            "last_checkin": self.last_checkin,
            "triggered": self.triggered,
            "triggered_by": self.triggered_by,
            "triggered_at": self.triggered_at,
            "cancelled": self.cancelled,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Inheritance":
        data = data.copy()
        data["heirs"] = [Heir.from_dict(h) for h in data.get("heirs", [])]
        return cls(**data)

    def __repr__(self):
        return (f"Inheritance({self.id}, {len(self.heirs)} heirs, "
                f"timeout={self.timeout_days}d, status={self.status()})")


class InheritanceManager:
    """Менеджер Dead Man's Switch."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.switches: dict = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("switches", []):
                sw = Inheritance.from_dict(item)
                self.switches[sw.id] = sw
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить inheritance: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"switches": [s.to_dict() for s in self.switches.values()]},
                      f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    def create(self, owner: str, heirs: list,
               timeout_days: int = DEFAULT_TIMEOUT_DAYS,
               note: str = "") -> Inheritance:
        if not is_valid_address(owner):
            raise ValueError("Невалидный адрес владельца")
        if not heirs:
            raise ValueError("Нужен хотя бы один наследник")
        if len(heirs) > MAX_HEIRS:
            raise ValueError(f"Максимум {MAX_HEIRS} наследников")
        if timeout_days < MIN_TIMEOUT_DAYS:
            raise ValueError(f"Минимальный таймаут — {MIN_TIMEOUT_DAYS} дней")

        total = 0.0
        for h in heirs:
            if not is_valid_address(h.address):
                raise ValueError(f"Невалидный адрес наследника: {h.address}")
            if h.address == owner:
                raise ValueError("Владелец не может быть своим наследником")
            total += h.share_percent

        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Сумма долей должна быть 100 (сейчас {total:.2f})")

        for existing in self.switches.values():
            if existing.owner == owner and existing.is_active():
                raise ValueError(
                    f"У владельца уже есть активный switch {existing.id}. "
                    f"Отмените его перед созданием нового."
                )

        for _ in range(10):
            sid = generate_id()
            if sid not in self.switches:
                break
        else:
            raise RuntimeError("Не удалось сгенерировать ID")

        now = time.time()
        sw = Inheritance(
            id=sid,
            owner=owner,
            heirs=heirs,
            timeout_days=timeout_days,
            created_at=now,
            last_checkin=now,
            note=note,
        )
        self.switches[sid] = sw
        self._save()
        return sw

    def check_in(self, owner: str):
        for sw in self.switches.values():
            if sw.owner == owner and sw.is_active():
                old_checkin = sw.last_checkin
                sw.last_checkin = time.time()
                self._save()
                delta_days = (sw.last_checkin - old_checkin) / 86400
                return True, f"Check-in обновлён (прошло {delta_days:.2f} дней)", sw
        return False, f"Активный switch не найден для {owner[:20]}...", None

    def trigger(self, sid: str, by: str,
                blockchain=None, available_balance=None):
        """
        Активировать switch. Создаёт транзакции owner → heirs.
        available_balance — опционально, доступный баланс без заморозки.
        Если None — берётся полный баланс (НЕ РЕКОМЕНДУЕТСЯ).
        """
        sw = self.get(sid)
        if sw is None:
            return False, "Switch не найден", []
        if sw.triggered:
            return False, "Уже активирован", []
        if sw.cancelled:
            return False, "Был отменён владельцем", []
        if not sw.is_triggerable():
            return False, (f"Владелец ещё активен. "
                          f"До срабатывания: {sw.time_left_str()}"), []

        heir_addrs = [h.address for h in sw.heirs]
        if by not in heir_addrs:
            return False, "Только наследник может активировать", []

        owner_wallet = self._find_wallet(sw.owner)
        if owner_wallet is None:
            return False, "Локальный кошелёк владельца не найден", []

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна для проведения транзакций", []

        # Берём доступный баланс (без заморозки)
        if available_balance is None:
            balance = bc.get_balance(sw.owner)
        else:
            balance = available_balance

        if balance <= 0:
            return False, (f"Доступный баланс владельца: "
                          f"{balance / config.SATOSHI:.4f} AIX — нечего передавать"), []

        tx_ids = []
        for heir in sw.heirs:
            amount = int(balance * heir.share_percent / 100.0)
            if amount <= 0:
                continue
            tx = Transaction(
                sender=sw.owner,
                recipient=heir.address,
                amount=amount,
                message=sw.note or f"Наследие от {sw.owner[:20]}...",
            )
            owner_wallet.sign_transaction(tx)
            ok, msg = tx.is_valid()
            if not ok:
                return False, f"Транзакция невалидна: {msg}", []
            ok, msg = bc.mempool.add(tx)
            if not ok:
                return False, f"Не добавлено в mempool: {msg}", []
            tx_ids.append(tx.tx_id())

        sw.triggered = True
        sw.triggered_by = by
        sw.triggered_at = time.time()
        self._save()
        return True, (f"Создано {len(tx_ids)} транзакций "
                     f"(от {balance / config.SATOSHI:.4f} AIX)"), tx_ids

    def cancel(self, sid: str, by: str):
        sw = self.get(sid)
        if sw is None:
            return False, "Не найден"
        if sw.triggered:
            return False, "Уже активирован — нельзя отменить"
        if sw.cancelled:
            return False, "Уже отменён"
        if sw.owner != by:
            return False, "Только владелец может отменить"
        sw.cancelled = True
        self._save()
        return True, "OK"

    def get(self, sid: str) -> Optional[Inheritance]:
        return self.switches.get(sid.upper())

    def list_by_owner(self, address: str) -> list:
        return [s for s in self.switches.values() if s.owner == address]

    def list_by_heir(self, address: str) -> list:
        return [s for s in self.switches.values()
                if any(h.address == address for h in s.heirs)]

    def list_active(self) -> list:
        return [s for s in self.switches.values() if s.is_active()]

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
        return len(self.switches)

    def __repr__(self):
        return f"InheritanceManager({len(self)} switches)"