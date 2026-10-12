"""AIX OS — DAO (#13).

Governance на базе Proof of Contribution.

Жизненный цикл:
1. Держатель SBT-медали создаёт proposal (TEXT или SPEND)
2. Другие держатели SBT голосуют: yes / no
3. Вес голоса = sbt_manager.reputation(voter)
4. Через VOTING_PERIOD_BLOCKS блоков — голосование закрывается
5. Если кворум (>=30% всей репутации SBT) и yes > no → passed
6. Через EXECUTION_DELAY_BLOCKS блоков — можно вызвать execute()
7. execute() для SPEND → poc_manager.pay(contribution_id)
8. execute() для TEXT → помечает executed

Хранение: data/dao_{port}.json
"""

import json
import random
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

ID_PREFIX = "DAO"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

QUORUM_PERCENT = 30
PASS_THRESHOLD = 50
VOTING_PERIOD_BLOCKS = 100
EXECUTION_DELAY_BLOCKS = 20
MIN_TITLE_LEN = 5
MAX_TITLE_LEN = 120
MAX_DESCRIPTION_LEN = 2000

PROPOSAL_KINDS = {
    "TEXT":  "Текстовое предложение (сигнал)",
    "SPEND": "Выплата из PoC-пула",
}


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


# =============================================================================
# PROPOSAL
# =============================================================================

@dataclass
class Proposal:
    id: str
    author: str
    title: str
    description: str
    kind: str
    payload: dict = field(default_factory=dict)
    created_at: float = 0.0
    created_height: int = 0
    voting_ends_at_height: int = 0
    execution_ready_at_height: int = 0
    votes: dict = field(default_factory=dict)
    status: str = "voting"          # voting | passed | rejected | executed | cancelled
    executed_at: float = 0.0
    executed_tx_id: str = ""
    cancelled_by: str = ""

    def yes_weight(self) -> int:
        return sum(v["weight"] for v in self.votes.values() if v["choice"] == "yes")

    def no_weight(self) -> int:
        return sum(v["weight"] for v in self.votes.values() if v["choice"] == "no")

    def total_weight(self) -> int:
        return self.yes_weight() + self.no_weight()

    def votes_count(self) -> int:
        return len(self.votes)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Proposal":
        return cls(**data)

    def __repr__(self):
        return (f"Proposal({self.id}, {self.kind}, {self.status}, "
                f"yes={self.yes_weight()}, no={self.no_weight()})")


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class DAOManager:
    """Менеджер DAO. Сохраняется на диск."""

    def __init__(self, storage_path, blockchain=None,
                 sbt_manager=None, poc_manager=None):
        self.storage_path = Path(storage_path)
        self.proposals: dict = {}
        self.blockchain = blockchain
        self.sbt = sbt_manager
        self.poc = poc_manager
        self._load()

    # ---------- IO ----------

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("proposals", []):
                p = Proposal.from_dict(item)
                self.proposals[p.id] = p
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить DAO: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"proposals": [p.to_dict() for p in self.proposals.values()]},
                f, ensure_ascii=False, indent=2,
            )
        tmp.replace(self.storage_path)

    # ---------- высота ----------

    def _current_height(self) -> int:
        if self.blockchain is not None:
            return self.blockchain.height()
        return 0

    # ---------- проверки ----------

    def _total_reputation(self) -> int:
        """Сумма репутации всех SBT-держателей (без повторов)."""
        if self.sbt is None:
            return 0
        seen = set()
        total = 0
        for m in self.sbt.medals:
            if m.revoked:
                continue
            if m.owner in seen:
                continue
            seen.add(m.owner)
            total += self.sbt.reputation(m.owner)
        return total

    def _has_sbt(self, address: str) -> bool:
        if self.sbt is None:
            return False
        return len(self.sbt.medals_of(address)) > 0

    # ---------- создание ----------

    def create_proposal(self, author: str, title: str, description: str,
                        kind: str = "TEXT",
                        payload: Optional[dict] = None) -> tuple:
        kind = (kind or "TEXT").upper()
        if kind not in PROPOSAL_KINDS:
            return False, f"Неизвестный kind: {kind}. Доступно: {list(PROPOSAL_KINDS)}"

        if not self._has_sbt(author):
            return False, "Только держатель SBT-медали может создавать предложения"

        title = (title or "").strip()
        description = (description or "").strip()
        if len(title) < MIN_TITLE_LEN:
            return False, f"Title слишком короткий (мин {MIN_TITLE_LEN})"
        if len(title) > MAX_TITLE_LEN:
            return False, f"Title слишком длинный (макс {MAX_TITLE_LEN})"
        if len(description) > MAX_DESCRIPTION_LEN:
            return False, f"Description слишком длинный (макс {MAX_DESCRIPTION_LEN})"

        payload = payload or {}
        if kind == "SPEND":
            cid = payload.get("contribution_id", "")
            if not cid:
                return False, "SPEND требует payload.contribution_id"
            if self.poc is None:
                return False, "PoC-менеджер недоступен"
            c = self.poc.get(cid)
            if c is None:
                return False, f"Вклад {cid} не найден"
            if c.status != "confirmed":
                return False, f"Вклад {cid} не в статусе confirmed (сейчас: {c.status})"

        for _ in range(10):
            pid = generate_id()
            if pid not in self.proposals:
                break
        else:
            return False, "Не удалось сгенерировать ID"

        h = self._current_height()
        p = Proposal(
            id=pid,
            author=author,
            title=title,
            description=description,
            kind=kind,
            payload=payload,
            created_at=time.time(),
            created_height=h,
            voting_ends_at_height=h + VOTING_PERIOD_BLOCKS,
            execution_ready_at_height=h + VOTING_PERIOD_BLOCKS + EXECUTION_DELAY_BLOCKS,
        )
        self.proposals[pid] = p
        self._save()
        return True, pid

    # ---------- голосование ----------

    def vote(self, proposal_id: str, voter: str, choice: str) -> tuple:
        p = self.get(proposal_id)
        if p is None:
            return False, "Предложение не найдено"
        if p.status != "voting":
            return False, f"Голосование закрыто (статус: {p.status})"

        h = self._current_height()
        if h > p.voting_ends_at_height:
            return False, f"Период голосования истёк на блоке {p.voting_ends_at_height}"

        choice = (choice or "").lower().strip()
        if choice not in ("yes", "no"):
            return False, "Голос должен быть 'yes' или 'no'"

        if not self._has_sbt(voter):
            return False, "Только держатели SBT могут голосовать"

        if voter in p.votes:
            return False, "Вы уже голосовали (изменить нельзя)"

        weight = self.sbt.reputation(voter)
        if weight <= 0:
            return False, "Ваш вес = 0 (нет активных медалей)"

        p.votes[voter] = {"choice": choice, "weight": weight, "at": time.time()}
        self._save()
        return True, f"Голос учтён (вес {weight}, {choice})"

    # ---------- финализация ----------

    def tally(self, proposal_id: str) -> tuple:
        p = self.get(proposal_id)
        if p is None:
            return False, "Не найдено"
        if p.status != "voting":
            return False, f"Уже финализировано: {p.status}"
        h = self._current_height()
        if h <= p.voting_ends_at_height:
            left = p.voting_ends_at_height - h
            return False, f"Ещё рано. Осталось блоков: {left}"
        self._finalize(p)
        return True, p.status

    def _finalize(self, p: Proposal):
        total_rep = self._total_reputation()
        voted = p.total_weight()
        quorum_ok = (total_rep > 0 and (voted * 100 / total_rep) >= QUORUM_PERCENT)

        if not quorum_ok:
            p.status = "rejected"
        else:
            yes = p.yes_weight()
            total = p.total_weight()
            if total > 0 and (yes * 100 / total) > PASS_THRESHOLD:
                p.status = "passed"
            else:
                p.status = "rejected"
        self._save()

    # ---------- исполнение ----------

    def execute(self, proposal_id: str, by: str = "") -> tuple:
        p = self.get(proposal_id)
        if p is None:
            return False, "Не найдено"
        if p.status != "passed":
            return False, f"Можно исполнить только passed (сейчас: {p.status})"

        h = self._current_height()
        if h < p.execution_ready_at_height:
            left = p.execution_ready_at_height - h
            return False, f"Timelock. Осталось блоков: {left}"

        if p.kind == "SPEND":
            if self.poc is None:
                return False, "PoC-менеджер недоступен"
            cid = p.payload.get("contribution_id", "")
            ok, msg = self.poc.pay(cid, blockchain=self.blockchain)
            if not ok:
                return False, f"Ошибка выплаты: {msg}"
            p.executed_tx_id = msg
            p.status = "executed"
            p.executed_at = time.time()
            self._save()
            return True, msg

        if p.kind == "TEXT":
            p.status = "executed"
            p.executed_at = time.time()
            p.executed_tx_id = f"TEXT-{p.id}"
            self._save()
            return True, "TEXT помечен как исполненный"

        return False, f"kind {p.kind} не исполняется автоматически"

    # ---------- отмена ----------

    def cancel(self, proposal_id: str, by: str) -> tuple:
        p = self.get(proposal_id)
        if p is None:
            return False, "Не найдено"
        if p.author != by:
            return False, "Только автор может отменить"
        if p.status != "voting":
            return False, f"Нельзя отменить в статусе {p.status}"
        p.status = "cancelled"
        p.cancelled_by = by
        self._save()
        return True, "Отменено"

    # ---------- просмотр ----------

    def get(self, proposal_id: str) -> Optional[Proposal]:
        return self.proposals.get(proposal_id.upper())

    def list_all(self, limit: int = 50) -> list:
        return sorted(self.proposals.values(),
                      key=lambda p: p.created_at, reverse=True)[:limit]

    def list_by_status(self, status: str) -> list:
        return [p for p in self.proposals.values() if p.status == status]

    def list_by_author(self, address: str) -> list:
        return [p for p in self.proposals.values() if p.author == address]

    # ---------- статистика ----------

    def stats(self) -> dict:
        by_status = {}
        by_kind = {}
        for p in self.proposals.values():
            by_status[p.status] = by_status.get(p.status, 0) + 1
            by_kind[p.kind] = by_kind.get(p.kind, 0) + 1
        return {
            "total": len(self.proposals),
            "by_status": by_status,
            "by_kind": by_kind,
            "total_reputation": self._total_reputation(),
            "quorum_percent": QUORUM_PERCENT,
            "pass_threshold": PASS_THRESHOLD,
            "voting_blocks": VOTING_PERIOD_BLOCKS,
            "execution_delay_blocks": EXECUTION_DELAY_BLOCKS,
        }

    # ---------- синхронизация ----------

    def export_all(self) -> list:
        return [p.to_dict() for p in self.proposals.values()]

    def import_proposal(self, data: dict) -> tuple:
        try:
            new_p = Proposal.from_dict(data)
        except Exception as e:
            return False, f"ошибка парсинга: {e}"

        existing = self.proposals.get(new_p.id)
        if existing is None:
            self.proposals[new_p.id] = new_p
            self._save()
            return True, "добавлен"

        order = {"voting": 0, "rejected": 1, "cancelled": 1,
                 "passed": 2, "executed": 3}
        if order.get(new_p.status, 0) > order.get(existing.status, 0):
            self.proposals[new_p.id] = new_p
            self._save()
            return True, "обновлён"

        if len(new_p.votes) > len(existing.votes):
            self.proposals[new_p.id] = new_p
            self._save()
            return True, "голоса обновлены"

        return True, "уже актуален"

    def __len__(self):
        return len(self.proposals)

    def __repr__(self):
        return f"DAOManager({len(self.proposals)} proposals)"