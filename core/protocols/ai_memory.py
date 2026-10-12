"""
AIX OS — AI Memory (#AI-1).

Память AI на блокчейне.

Идея: ИИ — душа AIX OS. И у него должна быть память.
Каждое важное событие в жизни проекта записывается как "воспоминание":
- Сессия начата/завершена
- Milestone достигнут
- Баг найден/исправлен
- Принято решение
- Что-то новое изучено

Зачем:
- AI не забывает между сессиями (CONTEXT + Memory)
- История проекта в структурированном виде
- Прозрачность для сообщества: что AI делал и почему
- Мета-фича: AI пишет сам о себе

Хранение: data/ai_memory.json
"""

import json
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


ID_PREFIX = "MEM"
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

KINDS = {
    "SESSION_START": {"emoji": "🚀", "title": "Начало сессии"},
    "SESSION_END":   {"emoji": "🏁", "title": "Конец сессии"},
    "MILESTONE":     {"emoji": "🏆", "title": "Milestone"},
    "BUG_FOUND":     {"emoji": "🐛", "title": "Найден баг"},
    "BUG_FIXED":     {"emoji": "🔧", "title": "Баг исправлен"},
    "DECISION":      {"emoji": "⚖️", "title": "Принято решение"},
    "LEARNING":      {"emoji": "📚", "title": "Урок"},
    "IDEA":          {"emoji": "💡", "title": "Идея"},
    "THOUGHT":       {"emoji": "💭", "title": "Мысль"},
}

PRIORITIES = {
    "CRITICAL":  {"weight": 100, "emoji": "🔴"},
    "IMPORTANT": {"weight": 50,  "emoji": "🟡"},
    "NORMAL":    {"weight": 10,  "emoji": "🟢"},
    "EPHEMERAL": {"weight": 1,   "emoji": "⚪"},
}

AIX_CORE = "AIX-CORE"


def generate_id() -> str:
    p1 = "".join(random.choices(ID_ALPHABET, k=4))
    p2 = "".join(random.choices(ID_ALPHABET, k=4))
    return f"{ID_PREFIX}-{p1}-{p2}"


@dataclass
class Memory:
    """Одно воспоминание AI."""
    id: str
    session_id: str
    kind: str
    priority: str
    title: str
    body: str = ""
    tags: list = field(default_factory=list)
    related_tx: str = ""
    related_block: int = -1
    created_at: float = 0.0
    created_by: str = AIX_CORE

    def emoji(self) -> str:
        return KINDS.get(self.kind, {}).get("emoji", "📌")

    def kind_title(self) -> str:
        return KINDS.get(self.kind, {}).get("title", self.kind)

    def priority_emoji(self) -> str:
        return PRIORITIES.get(self.priority, {}).get("emoji", "⚪")

    def weight(self) -> int:
        return PRIORITIES.get(self.priority, {}).get("weight", 1)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(**data)

    def __repr__(self):
        return f"Memory({self.id}, {self.kind}, {self.priority}, {self.title[:30]})"


class AIMemoryManager:
    """Менеджер памяти AI. Локальный для ноды."""

    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.memories: list[Memory] = []
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("memories", []):
                self.memories.append(Memory.from_dict(item))
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить AI Memory: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"memories": [m.to_dict() for m in self.memories]},
                f, ensure_ascii=False, indent=2,
            )
        tmp.replace(self.storage_path)

    # =========================================================================
    # ЗАПИСЬ
    # =========================================================================

    def remember(
        self,
        title: str,
        body: str = "",
        kind: str = "THOUGHT",
        priority: str = "NORMAL",
        tags: Optional[list] = None,
        session_id: str = "",
        related_tx: str = "",
        related_block: int = -1,
    ) -> Memory:
        """Записать воспоминание."""
        if kind not in KINDS:
            raise ValueError(f"Неизвестный kind '{kind}'. Доступные: {', '.join(KINDS.keys())}")
        if priority not in PRIORITIES:
            raise ValueError(f"Неизвестный priority '{priority}'. Доступные: {', '.join(PRIORITIES.keys())}")

        if not session_id:
            session_id = time.strftime("%Y-%m-%d")

        for _ in range(10):
            mid = generate_id()
            if not any(m.id == mid for m in self.memories):
                break
        else:
            raise RuntimeError("Не удалось сгенерировать ID")

        mem = Memory(
            id=mid,
            session_id=session_id,
            kind=kind,
            priority=priority,
            title=title,
            body=body,
            tags=tags or [],
            related_tx=related_tx,
            related_block=related_block,
            created_at=time.time(),
        )
        self.memories.append(mem)
        self._save()
        return mem

    def import_memory(self, data: dict) -> tuple:
        """Импорт воспоминания из внешнего источника (для sync)."""
        try:
            mem = Memory.from_dict(data)
        except Exception as e:
            return False, f"ошибка парсинга: {e}"

        if any(m.id == mem.id for m in self.memories):
            return True, "уже есть"

        self.memories.append(mem)
        self._save()
        return True, "добавлен"

    # =========================================================================
    # ЧТЕНИЕ
    # =========================================================================

    def all(self, limit: int = 0) -> list[Memory]:
        """Все воспоминания (от новых к старым)."""
        sorted_mems = sorted(self.memories, key=lambda m: m.created_at, reverse=True)
        if limit:
            return sorted_mems[:limit]
        return sorted_mems

    def latest(self, n: int = 10) -> list[Memory]:
        return self.all(limit=n)

    def by_kind(self, kind: str) -> list[Memory]:
        return [m for m in self.all() if m.kind == kind.upper()]

    def by_priority(self, priority: str) -> list[Memory]:
        return [m for m in self.all() if m.priority == priority.upper()]

    def by_tag(self, tag: str) -> list[Memory]:
        tag = tag.lower()
        return [m for m in self.all() if tag in [t.lower() for t in m.tags]]

    def by_session(self, session_id: str) -> list[Memory]:
        return [m for m in self.all() if m.session_id == session_id]

    def sessions(self) -> list[str]:
        """Список всех session_id (уникальных), от новых к старым."""
        seen = []
        for m in self.all():
            if m.session_id not in seen:
                seen.append(m.session_id)
        return seen

    def critical(self) -> list[Memory]:
        """Все CRITICAL воспоминания."""
        return self.by_priority("CRITICAL")

    def search(self, query: str) -> list[Memory]:
        """Поиск по title, body, tags."""
        q = query.lower()
        return [
            m for m in self.all()
            if q in m.title.lower()
            or q in m.body.lower()
            or any(q in t.lower() for t in m.tags)
        ]

    # =========================================================================
    # БРИФ ДЛЯ AI
    # =========================================================================

    def brief(self, max_critical: int = 10, max_latest: int = 20) -> str:
        """Сгенерировать текстовый бриф для AI."""
        lines = []
        lines.append("# 🧠 AIX Memory — Brief")
        lines.append("")
        lines.append(f"Всего воспоминаний: **{len(self.memories)}**")
        lines.append(f"Сессий: **{len(self.sessions())}**")
        lines.append("")

        # CRITICAL
        critical = self.critical()[:max_critical]
        if critical:
            lines.append("## 🔴 CRITICAL (не забыть!)")
            lines.append("")
            for m in critical:
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.created_at))
                lines.append(f"- **{m.title}** — _{ts}_")
                if m.body:
                    lines.append(f"  > {m.body}")
                if m.tags:
                    lines.append(f"  `теги: {', '.join(m.tags)}`")
            lines.append("")

        # Последние
        lines.append(f"## 📜 Последние {max_latest}")
        lines.append("")
        for m in self.latest(max_latest):
            ts = time.strftime("%m-%d %H:%M", time.localtime(m.created_at))
            lines.append(f"- {m.emoji()} **{m.title}** — _{ts}_ `{m.kind}/{m.priority}`")
            if m.body and len(m.body) < 200:
                lines.append(f"  > {m.body}")
        lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def stats(self) -> dict:
        by_kind = {}
        by_priority = {}
        for m in self.memories:
            by_kind[m.kind] = by_kind.get(m.kind, 0) + 1
            by_priority[m.priority] = by_priority.get(m.priority, 0) + 1

        return {
            "total": len(self.memories),
            "sessions": len(self.sessions()),
            "by_kind": by_kind,
            "by_priority": by_priority,
            "first_at": self.memories[0].created_at if self.memories else 0,
            "last_at": self.memories[-1].created_at if self.memories else 0,
        }

    def export_all(self) -> list:
        return [m.to_dict() for m in self.memories]

    def __len__(self):
        return len(self.memories)

    def __repr__(self):
        return f"AIMemoryManager({len(self.memories)} memories, {len(self.sessions())} sessions)"


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    print("🧠 Тестирую AI Memory...\n")

    import tempfile
    tmp = Path(tempfile.gettempdir()) / "test_ai_memory.json"
    if tmp.exists():
        tmp.unlink()

    mgr = AIMemoryManager(tmp)

    print("1. Записываю воспоминания:")
    m1 = mgr.remember("Начало теста", kind="SESSION_START", priority="NORMAL")
    print(f"   {m1}")

    m2 = mgr.remember(
        "Пофиксил баг с mempool",
        body="Добавил remove_many в replace_chain",
        kind="BUG_FIXED",
        priority="IMPORTANT",
        tags=["mempool", "chain"],
    )
    print(f"   {m2}")

    m3 = mgr.remember(
        "Критично: не менять PHONE_SALT",
        body="Иначе все хеши номеров сломаются",
        kind="LEARNING",
        priority="CRITICAL",
        tags=["contacts", "crypto"],
    )
    print(f"   {m3}")

    print(f"\n2. Всего: {len(mgr)}")
    print(f"   Сессий: {mgr.sessions()}")

    print(f"\n3. CRITICAL:")
    for m in mgr.critical():
        print(f"   {m.priority_emoji()} {m.title}")

    print(f"\n4. Поиск 'mempool':")
    for m in mgr.search("mempool"):
        print(f"   {m.emoji()} {m.title}")

    print(f"\n5. Бриф:")
    print("-" * 50)
    print(mgr.brief())
    print("-" * 50)

    tmp.unlink()
    print("\n✅ AI Memory работает.")