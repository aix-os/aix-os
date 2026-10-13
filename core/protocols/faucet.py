"""
AIX OS — Faucet (кран).

Публичная раздача первых AIX. Один адрес — один раз,
один IP — раз в 24 часа, глобальный лимит в час.

Хранит журнал в JSON-файле (data/faucet_log.json).

Публичный API:
    FaucetManager(path, blockchain=...)
    .set_treasury(name)          — назначить кошелёк-казначей
    .treasury_name                — имя кошелька-казначея
    .stats()                      — сводка
    .can_claim(addr, ip)          — проверка без списания
    .claim(addr, ip)              — попытка выдать
    .log(limit)                   — последние записи
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Размер выдачи
FAUCET_AMOUNT_AIX = 10

# Лимиты
COOLDOWN_IP_HOURS = 24
GLOBAL_HOURLY_LIMIT = 100

# Файл сохраняется атомарно с .bak


@dataclass
class FaucetEntry:
    address: str
    ip: str
    amount_aix: float
    tx_id: str
    ts: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FaucetManager:
    """Менеджер крана. Потокобезопасен (lock)."""

    def __init__(self, path: str | os.PathLike, blockchain=None):
        self.path = Path(path)
        self.blockchain = blockchain
        self._lock = threading.RLock()
        self._entries: list[FaucetEntry] = []
        self._treasury: str = ""        # имя кошелька-казначея
        self._load()

    # ---------- загрузка / сохранение ----------

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        self._treasury = data.get("treasury", "") or ""
        self._entries = []
        for e in data.get("entries", []):
            try:
                self._entries.append(FaucetEntry(
                    address=e["address"], ip=e.get("ip", ""),
                    amount_aix=float(e["amount_aix"]),
                    tx_id=e.get("tx_id", ""),
                    ts=float(e["ts"]),
                ))
            except Exception:
                continue

    def _save(self) -> None:
        payload = {
            "treasury": self._treasury,
            "entries": [e.to_dict() for e in self._entries],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Атомарная замена + .bak
        if self.path.exists():
            bak = self.path.with_suffix(self.path.suffix + ".bak")
            try:
                bak.write_bytes(self.path.read_bytes())
            except Exception:
                pass
        tmp.replace(self.path)

    # ---------- казначей ----------

    def set_treasury(self, name: str) -> None:
        with self._lock:
            self._treasury = (name or "").strip()
            self._save()

    @property
    def treasury_name(self) -> str:
        return self._treasury

    # ---------- проверки ----------

    def _now(self) -> float:
        return time.time()

    def _ip_last_claim(self, ip: str) -> float | None:
        for e in reversed(self._entries):
            if e.ip == ip:
                return e.ts
        return None

    def _address_used(self, address: str) -> bool:
        return any(e.address == address for e in self._entries)

    def _claims_last_hour(self) -> int:
        cutoff = self._now() - 3600
        return sum(1 for e in self._entries if e.ts >= cutoff)

    def can_claim(self, address: str, ip: str) -> tuple[bool, str]:
        """Проверка без записи. Возвращает (ok, reason)."""
        address = (address or "").strip()
        ip = (ip or "").strip()

        if not address.startswith("AIX") or len(address) < 30:
            return False, "Невалидный AIX-адрес"

        if self._address_used(address):
            return False, "Этот адрес уже получал AIX"

        last = self._ip_last_claim(ip)
        if last is not None:
            elapsed_hours = (self._now() - last) / 3600
            if elapsed_hours < COOLDOWN_IP_HOURS:
                wait = COOLDOWN_IP_HOURS - elapsed_hours
                return False, f"С этого IP уже брали. Подожди ещё {wait:.1f} ч."

        if self._claims_last_hour() >= GLOBAL_HOURLY_LIMIT:
            return False, "Кран временно перегружен, попробуй позже"

        return True, ""

    # ---------- выдача ----------

    def claim(self, address: str, ip: str,
              wallet_loader=None, sender=None) -> tuple[bool, dict[str, Any]]:
        """Попытка выдать AIX.

        wallet_loader — функция, которая принимает имя кошелька и возвращает
                        объект с полями address / private_key.
        sender        — функция, которая отправляет транзакцию:
                        (sender_addr, recipient_addr, amount_aix, private_key) -> tx_id

        Если wallet_loader/sender не переданы — только проверка и запись
        (используется в тестах).
        """
        with self._lock:
            ok, reason = self.can_claim(address, ip)
            if not ok:
                return False, {"error": reason}

            if not self._treasury:
                return False, {"error": "Казначей не назначен"}

            if wallet_loader is None or sender is None:
                # Запись без реальной отправки (для тестов)
                entry = FaucetEntry(
                    address=address, ip=ip,
                    amount_aix=FAUCET_AMOUNT_AIX,
                    tx_id="DRY-RUN", ts=self._now(),
                )
                self._entries.append(entry)
                self._save()
                return True, {
                    "status": "dry_run",
                    "address": address,
                    "amount_aix": FAUCET_AMOUNT_AIX,
                    "tx_id": "DRY-RUN",
                }

            # Реальная отправка
            try:
                w = wallet_loader(self._treasury)
                sender_addr = w.address
                private_key = w.private_key
            except Exception as e:
                return False, {"error": f"Кошелёк-казначей недоступен: {e}"}

            try:
                tx_id = sender(sender_addr, address,
                               FAUCET_AMOUNT_AIX, private_key)
            except Exception as e:
                return False, {"error": f"Отправка не удалась: {e}"}

            entry = FaucetEntry(
                address=address, ip=ip,
                amount_aix=FAUCET_AMOUNT_AIX,
                tx_id=tx_id or "", ts=self._now(),
            )
            self._entries.append(entry)
            self._save()

            return True, {
                "status": "sent",
                "address": address,
                "amount_aix": FAUCET_AMOUNT_AIX,
                "tx_id": tx_id,
                "treasury": self._treasury,
            }

    # ---------- отчёты ----------

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_sent = sum(e.amount_aix for e in self._entries)
            last_hour = self._claims_last_hour()
            last_24h = sum(
                1 for e in self._entries
                if e.ts >= self._now() - 86400
            )
            return {
                "treasury": self._treasury,
                "amount_per_claim_aix": FAUCET_AMOUNT_AIX,
                "cooldown_ip_hours": COOLDOWN_IP_HOURS,
                "hourly_limit": GLOBAL_HOURLY_LIMIT,
                "total_claims": len(self._entries),
                "total_sent_aix": round(total_sent, 6),
                "claims_last_hour": last_hour,
                "claims_last_24h": last_24h,
            }

    def log(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            tail = self._entries[-int(limit):] if limit else self._entries
            return [e.to_dict() for e in reversed(tail)]

    def count(self) -> int:
        return len(self._entries)