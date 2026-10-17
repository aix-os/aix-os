"""
AIX OS — Proof of Contribution (#3).

Механизм награды за реальный вклад в проект.

Как работает:
1. Фонд пополняется: любой отправляет AIX в POC-POOL
2. Contributor создаёт вклад: "сделал X, прошу Y AIX"
3. Ревьюеры подтверждают (нужно N голосов — зависит от размера)
4. Когда кворум собран — AIX выплачивается из пула

Категории вклада:
- CODE, TRANSLATION, DOCS, BUG, DESIGN, PROMO, COMMUNITY, EDUCATION

Уровни награды:
- MICRO:  <= 100 AIX   — 1 подтверждение
- SMALL:  <= 1000 AIX  — 2 подтверждения
- MEDIUM: <= 5000 AIX  — 3 подтверждения
- LARGE:  > 5000 AIX   — 5 подтверждений

⚠️ POC-POOL — системный адрес, как COINBASE и LOTTERY.

Хранение: data/poc_{port}.json
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
from core.wallet import Wallet
from crypto.address import is_valid_address
import config


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

ID_PREFIX = "POC"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Системный адрес-получатель для донатов
POC_POOL_ADDRESS = "POC-POOL"

# Категории вклада
CATEGORIES = {
    "CODE":        {"title": "Код", "emoji": "💻"},
    "TRANSLATION": {"title": "Перевод", "emoji": "🌍"},
    "DOCS":        {"title": "Документация", "emoji": "📚"},
    "BUG":         {"title": "Баг-репорт", "emoji": "🐛"},
    "DESIGN":      {"title": "Дизайн", "emoji": "🎨"},
    "PROMO":       {"title": "Продвижение", "emoji": "📢"},
    "COMMUNITY":   {"title": "Помощь сообществу", "emoji": "🤝"},
    "EDUCATION":   {"title": "Обучение", "emoji": "🎓"},
}

# Уровни награды: (максимум AIX, нужно подтверждений)
REWARD_LEVELS = [
    ("MICRO",  100,  1),
    ("SMALL",  1000, 2),
    ("MEDIUM", 5000, 3),
    ("LARGE",  float("inf"), 5),
]


def get_required_confirmations(reward_aix: float) -> tuple:
    """Возвращает (level_name, required_count) для суммы награды."""
    for name, max_aix, count in REWARD_LEVELS:
        if reward_aix <= max_aix:
            return name, count
    return "LARGE", 5


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


# =============================================================================
# КОНТРИБУЦИЯ
# =============================================================================

@dataclass
class Contribution:
    """Один вклад в проект."""
    id: str
    contributor: str                # AIX-адрес автора
    category: str                   # CODE / TRANSLATION / ...
    title: str                      # краткое описание
    description: str                # подробности
    proof_url: str                  # ссылка на доказательство (github, PR и т.д.)
    requested_reward: int           # запрошенная сумма в атомарных единицах
    reward_level: str               # MICRO / SMALL / MEDIUM / LARGE
    required_confirmations: int     # сколько нужно для кворума
    confirmations: list = field(default_factory=list)   # [address, ...]
    rejections: list = field(default_factory=list)      # [{"by": addr, "reason": str}]
    status: str = "pending"         # pending / confirmed / paid / rejected
    submitted_at: float = 0.0
    confirmed_at: float = 0.0
    paid_at: float = 0.0
    paid_tx_id: str = ""

    def reward_aix(self) -> float:
        return self.requested_reward / config.SATOSHI

    def confirmations_count(self) -> int:
        return len(self.confirmations)

    def is_confirmed(self) -> bool:
        return self.confirmations_count() >= self.required_confirmations

    def progress_str(self) -> str:
        return f"{self.confirmations_count()}/{self.required_confirmations}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Contribution":
        return cls(**data)

    def __repr__(self):
        return f"Contribution({self.id}, {self.category}, {self.reward_aix():.2f} AIX, {self.status})"


# =============================================================================
# REWARD POOL
# =============================================================================

@dataclass
class RewardPool:
    """Фонд наград за вклад."""
    total_donated: int = 0          # всего пожертвовано
    total_paid: int = 0             # всего выплачено
    donations: list = field(default_factory=list)   # [{address, amount, time}, ...]
    payouts: list = field(default_factory=list)     # [{address, amount, contribution_id, time}, ...]

    def balance(self) -> int:
        return self.total_donated - self.total_paid

    def balance_aix(self) -> float:
        return self.balance() / config.SATOSHI

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RewardPool":
        return cls(**data)


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class PoCManager:
    """Менеджер Proof of Contribution."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.contributions: dict = {}   # id -> Contribution
        self.pool = RewardPool()
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("contributions", []):
                c = Contribution.from_dict(item)
                self.contributions[c.id] = c
            if "pool" in data:
                self.pool = RewardPool.from_dict(data["pool"])
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить PoC: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "contributions": [c.to_dict() for c in self.contributions.values()],
                "pool": self.pool.to_dict(),
            }, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # ФОНД
    # =========================================================================

    def donate(self, address: str, amount: int,
               blockchain=None) -> tuple:
        """Пожертвовать AIX в фонд."""
        if amount <= 0:
            return False, "Сумма должна быть положительной"
        if not is_valid_address(address):
            return False, "Невалидный адрес"

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна"

        # Проверяем баланс
        balance = bc.get_balance(address)
        if balance < amount:
            return False, f"Недостаточно AIX. У вас: {balance / config.SATOSHI:.2f}"

        # Ищем кошелёк
        wallet = self._find_wallet(address)
        if wallet is None:
            return False, "Локальный кошелёк не найден"

        # Создаём транзакцию address → POC-POOL
        tx = Transaction(
            sender=address,
            recipient=POC_POOL_ADDRESS,
            amount=amount,
            message=f"💚 Donation to PoC pool",
        )
        wallet.sign_transaction(tx)
        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}"
        ok, msg = bc.mempool.add(tx)
        if not ok:
            return False, f"Не добавлено в mempool: {msg}"

        self.pool.total_donated += amount
        self.pool.donations.append({
            "address": address,
            "amount": amount,
            "time": time.time(),
        })
        self._save()
        return True, tx.tx_id()

    def balance(self) -> int:
        return self.pool.balance()

    # =========================================================================
    # ВКЛАДЫ
    # =========================================================================

    def submit(self, contributor: str, category: str, title: str,
               description: str, requested_reward: int,
               proof_url: str = "") -> tuple:
        """Создать вклад."""
        if not is_valid_address(contributor):
            return False, "Невалидный адрес"
        if category not in CATEGORIES:
            return False, f"Неизвестная категория. Доступные: {', '.join(CATEGORIES.keys())}"
        if not title or len(title) > 100:
            return False, "Title обязателен (макс 100 символов)"
        if not description or len(description) > 1000:
            return False, "Description обязателен (макс 1000 символов)"
        if requested_reward <= 0:
            return False, "Сумма должна быть положительной"

        reward_aix = requested_reward / config.SATOSHI
        level, required = get_required_confirmations(reward_aix)

        # Проверяем, что в пуле хватает
        if self.pool.balance() < requested_reward:
            return False, (f"В фонде недостаточно AIX. "
                          f"Сейчас: {self.pool.balance_aix():.2f}, "
                          f"нужно: {reward_aix:.2f}")

        # Уникальный ID
        for _ in range(10):
            cid = generate_id()
            if cid not in self.contributions:
                break
        else:
            return False, "Не удалось сгенерировать ID"

        c = Contribution(
            id=cid,
            contributor=contributor,
            category=category,
            title=title,
            description=description,
            proof_url=proof_url,
            requested_reward=requested_reward,
            reward_level=level,
            required_confirmations=required,
            submitted_at=time.time(),
        )
        self.contributions[cid] = c
        self._save()
        return True, cid

    def confirm(self, contribution_id: str, reviewer: str) -> tuple:
        """Подтвердить вклад."""
        c = self.get(contribution_id)
        if c is None:
            return False, "Вклад не найден"
        if c.status != "pending":
            return False, f"Нельзя подтвердить — статус {c.status}"
        if not is_valid_address(reviewer):
            return False, "Невалидный адрес ревьюера"
        if reviewer == c.contributor:
            return False, "Нельзя подтверждать свой собственный вклад"
        if reviewer in c.confirmations:
            return False, "Вы уже подтвердили этот вклад"

        c.confirmations.append(reviewer)

        if c.is_confirmed():
            c.status = "confirmed"
            c.confirmed_at = time.time()

        self._save()
        return True, "OK"

    def reject(self, contribution_id: str, reviewer: str, reason: str = "") -> tuple:
        """Отклонить вклад."""
        c = self.get(contribution_id)
        if c is None:
            return False, "Вклад не найден"
        if c.status != "pending":
            return False, f"Нельзя отклонить — статус {c.status}"
        if not is_valid_address(reviewer):
            return False, "Невалидный адрес"
        if reviewer == c.contributor:
            return False, "Нельзя отклонять свой вклад"
        if any(r["by"] == reviewer for r in c.rejections):
            return False, "Вы уже отклоняли этот вклад"

        c.rejections.append({"by": reviewer, "reason": reason, "time": time.time()})

        # Если отказов больше, чем нужно подтверждений — авто-reject
        if len(c.rejections) >= c.required_confirmations:
            c.status = "rejected"

        self._save()
        return True, "OK"

    def pay(self, contribution_id: str, blockchain=None) -> tuple:
        """Выплатить награду за подтверждённый вклад."""
        c = self.get(contribution_id)
        if c is None:
            return False, "Вклад не найден"
        if c.status == "paid":
            return False, "Уже выплачено"
        if c.status != "confirmed":
            return False, f"Вклад не подтверждён (статус: {c.status})"

        bc = blockchain or self.blockchain
        if bc is None:
            return False, "Нет блокчейна"

        if self.pool.balance() < c.requested_reward:
            return False, (f"В фонде недостаточно. "
                          f"Сейчас: {self.pool.balance_aix():.2f}, "
                          f"нужно: {c.reward_aix():.2f}")

        # Создаём системную транзакцию POC-POOL → contributor
        tx = Transaction(
            sender=POC_POOL_ADDRESS,
            recipient=c.contributor,
            amount=c.requested_reward,
            message=f"🧬 PoC reward: {c.id} — {c.title[:50]}",
        )

        ok, msg = tx.is_valid()
        if not ok:
            return False, f"Транзакция невалидна: {msg}"
        ok, msg = bc.mempool.add(tx)
        if not ok:
            return False, f"Не добавлено в mempool: {msg}"

        c.status = "paid"
        c.paid_at = time.time()
        c.paid_tx_id = tx.tx_id()
        self.pool.total_paid += c.requested_reward
        self.pool.payouts.append({
            "address": c.contributor,
            "amount": c.requested_reward,
            "contribution_id": c.id,
            "time": c.paid_at,
        })
        self._save()
        return True, tx.tx_id()

    # =========================================================================
    # ПРОСМОТР
    # =========================================================================

    def get(self, contribution_id: str) -> Optional[Contribution]:
        return self.contributions.get(contribution_id.upper())

    def list_by_contributor(self, address: str) -> list:
        return sorted(
            [c for c in self.contributions.values() if c.contributor == address],
            key=lambda c: c.submitted_at, reverse=True,
        )

    def list_by_status(self, status: str) -> list:
        return sorted(
            [c for c in self.contributions.values() if c.status == status],
            key=lambda c: c.submitted_at, reverse=True,
        )

    def list_confirmed_unpaid(self) -> list:
        return sorted(
            [c for c in self.contributions.values() if c.status == "confirmed"],
            key=lambda c: c.confirmed_at,
        )

    def list_all(self, limit: int = 50) -> list:
        return sorted(
            self.contributions.values(),
            key=lambda c: c.submitted_at, reverse=True,
        )[:limit]

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def stats(self) -> dict:
        by_status = {}
        for c in self.contributions.values():
            by_status[c.status] = by_status.get(c.status, 0) + 1

        by_category = {}
        for c in self.contributions.values():
            by_category[c.category] = by_category.get(c.category, 0) + 1

        return {
            "pool_balance_aix": self.pool.balance_aix(),
            "total_donated_aix": self.pool.total_donated / config.SATOSHI,
            "total_paid_aix": self.pool.total_paid / config.SATOSHI,
            "total_contributions": len(self.contributions),
            "by_status": by_status,
            "by_category": by_category,
            "donations_count": len(self.pool.donations),
            "payouts_count": len(self.pool.payouts),
        }

    def leaderboard(self, limit: int = 20) -> list:
        """Топ контрибьюторов: (address, count, total_reward_aix, paid_count)."""
        from collections import defaultdict
        scores = defaultdict(lambda: {"count": 0, "reward": 0, "paid": 0})
        for c in self.contributions.values():
            s = scores[c.contributor]
            s["count"] += 1
            if c.status in ("confirmed", "paid"):
                s["reward"] += c.requested_reward
            if c.status == "paid":
                s["paid"] += 1
        sorted_items = sorted(
            scores.items(),
            key=lambda kv: (-kv[1]["reward"], -kv[1]["count"]),
        )
        return [
            (addr, s["count"], s["reward"] / config.SATOSHI, s["paid"])
            for addr, s in sorted_items[:limit]
        ]

    # =========================================================================
    # СИНХРОНИЗАЦИЯ
    # =========================================================================

    def export_all(self) -> dict:
        return {
            "contributions": [c.to_dict() for c in self.contributions.values()],
            "pool": self.pool.to_dict(),
        }

    def import_contribution(self, data: dict) -> tuple:
        try:
            new_c = Contribution.from_dict(data)
        except Exception as e:
            return False, f"ошибка парсинга: {e}"

        existing = self.contributions.get(new_c.id)
        if existing is None:
            self.contributions[new_c.id] = new_c
            self._save()
            return True, "добавлен"
        # Если статус изменился на более продвинутый — обновляем
        status_order = {"pending": 0, "rejected": 1, "confirmed": 2, "paid": 3}
        if status_order.get(new_c.status, 0) > status_order.get(existing.status, 0):
            self.contributions[new_c.id] = new_c
            self._save()
            return True, "обновлён"
        return True, "уже актуален"

    def import_pool(self, data: dict) -> tuple:
        """
        Merge пула PoC.

        ✅ ИСПРАВЛЕНО (баг #2):
        Сравниваем И total_donated, И total_paid.
        Иначе нода, у которой был donated, но не было paid,
        не подтянет выплаты от соседа.

        Дополнительно сливаем donations/payouts по уникальным ключам,
        чтобы ничего не потерялось при частичной доставке событий.
        """
        try:
            new_pool = RewardPool.from_dict(data)
        except Exception as e:
            return False, f"ошибка парсинга pool: {e}"

        changed = False

        # Сливаем донаты по (address, time)
        existing_donations = {(d["address"], d["time"]) for d in self.pool.donations}
        for d in new_pool.donations:
            key = (d["address"], d["time"])
            if key not in existing_donations:
                self.pool.donations.append(d)
                self.pool.total_donated += d["amount"]
                existing_donations.add(key)
                changed = True

        # Сливаем выплаты по (address, contribution_id)
        existing_payouts = {(p["address"], p["contribution_id"])
                            for p in self.pool.payouts}
        for p in new_pool.payouts:
            key = (p["address"], p["contribution_id"])
            if key not in existing_payouts:
                self.pool.payouts.append(p)
                self.pool.total_paid += p["amount"]
                existing_payouts.add(key)
                changed = True

        if changed:
            self._save()
            return True, "pool обновлён (merge)"
        return True, "pool актуален"

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
        return len(self.contributions)

    def __repr__(self):
        return f"PoCManager({len(self.contributions)} contributions, pool={self.pool.balance_aix():.2f} AIX)"


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    print("🧬 Тестирую Proof of Contribution...\n")

    import tempfile
    tmp = Path(tempfile.gettempdir()) / "test_poc.json"
    if tmp.exists():
        tmp.unlink()

    mgr = PoCManager(tmp)

    alice = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
    bob = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"
    carol = "AIXTXkTCmPUzxkdjdB8eYvga9P7WKG8gTFArM"

    # 1. Донат (симулируем — без блокчейна)
    print("1. Донат в фонд (симуляция):")
    mgr.pool.total_donated += 10000 * 10**8
    mgr.pool.donations.append({"address": alice, "amount": 10000 * 10**8, "time": time.time()})
    print(f"   Фонд: {mgr.pool.balance_aix():.2f} AIX")
    print()

    # 2. Bob создаёт вклад
    print("2. Bob создаёт вклад (1500 AIX за код):")
    ok, cid = mgr.submit(
        contributor=bob,
        category="CODE",
        title="Реализовал P2P-сеть",
        description="Написал модуль peer_manager.py, добавил синхронизацию",
        requested_reward=1500 * 10**8,
        proof_url="https://github.com/aix-os/pr/42",
    )
    print(f"   {ok} — ID: {cid}")
    c = mgr.get(cid)
    print(f"   Уровень: {c.reward_level}, нужно подтверждений: {c.required_confirmations}")
    print()

    # 3. Alice подтверждает
    print("3. Alice подтверждает:")
    ok, msg = mgr.confirm(cid, alice)
    print(f"   {ok} — {msg}")
    print(f"   Прогресс: {c.progress_str()}")
    print()

    # 4. Bob пытается подтвердить себя
    print("4. Bob пытается подтвердить сам себя:")
    ok, msg = mgr.confirm(cid, bob)
    print(f"   {ok} — {msg}")
    print()

    # 5. Carol подтверждает
    print("5. Carol подтверждает:")
    ok, msg = mgr.confirm(cid, carol)
    print(f"   {ok} — {msg}")
    print(f"   Прогресс: {c.progress_str()}")
    print(f"   Статус: {c.status}")
    print()

    # 6. Статистика
    print("6. Статистика:")
    st = mgr.stats()
    print(f"   Всего вкладов: {st['total_contributions']}")
    print(f"   В фонде: {st['pool_balance_aix']:.2f} AIX")
    print(f"   По статусу: {st['by_status']}")
    print()

    # 7. Leaderboard
    print("7. Топ контрибьюторов:")
    for addr, count, reward, paid in mgr.leaderboard():
        print(f"   {addr[:20]}... — вкладов: {count}, заявлено: {reward:.2f} AIX, оплачено: {paid}")

    tmp.unlink()
    print("\n✅ Proof of Contribution работает.")