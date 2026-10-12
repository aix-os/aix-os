"""AIX OS — AI Memory (#AI-1).

Память AI-ассистента. Каждое важное событие — структурированное воспоминание.
Хранится в data/ai_memory.json (атомарная запись + .bak).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


KINDS = (
    "SESSION_START", "SESSION_END", "MILESTONE", "BUG_FIXED",
    "DECISION", "LEARNING", "IDEA", "THOUGHT",
)
PRIORITIES = ("CRITICAL", "IMPORTANT", "NORMAL", "EPHEMERAL")
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITIES)}

KIND_EMOJI = {
    "SESSION_START": "🚀", "SESSION_END": "🏁", "MILESTONE": "🏆",
    "BUG_FIXED": "🐛", "DECISION": "⚖️", "LEARNING": "📚",
    "IDEA": "💡", "THOUGHT": "💭",
}
PRIORITY_EMOJI = {
    "CRITICAL": "🔴", "IMPORTANT": "🟠", "NORMAL": "🟡", "EPHEMERAL": "⚪",
}


@dataclass
class Memory:
    text: str
    kind: str = "THOUGHT"
    priority: str = "NORMAL"
    tags: list = field(default_factory=list)
    session: str = ""
    ts: str = ""
    hash: str = ""
    chain_ref: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        return cls(
            text=d.get("text", ""),
            kind=d.get("kind", "THOUGHT"),
            priority=d.get("priority", "NORMAL"),
            tags=list(d.get("tags", [])),
            session=d.get("session", ""),
            ts=d.get("ts", ""),
            hash=d.get("hash", ""),
            chain_ref=d.get("chain_ref", ""),
        )

    def compute_hash(self) -> str:
        payload = json.dumps(
            {"text": self.text, "kind": self.kind, "priority": self.priority,
             "tags": self.tags, "session": self.session, "ts": self.ts},
            ensure_ascii=False, sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _current_session() -> str:
    return os.environ.get("AIX_SESSION") or datetime.now().strftime("%Y-%m-%d-session")


class AIMemoryManager:
    """JSON-хранитель памяти AI."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._memories: list[Memory] = []
        self._load()

    # ---------- IO ----------

    def _load(self) -> None:
        if not self.path.exists():
            self._memories = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            bak = self.path.with_suffix(self.path.suffix + ".bak")
            if bak.exists():
                with open(bak, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            else:
                raw = {"memories": []}

        items = raw if isinstance(raw, list) else raw.get("memories", [])
        self._memories = [Memory.from_dict(x) for x in items]

    def _save(self) -> None:
        data = {"memories": [m.to_dict() for m in self._memories]}
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent),
                                   prefix=".ai_memory_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            if self.path.exists():
                bak = self.path.with_suffix(self.path.suffix + ".bak")
                try:
                    bak.write_text(self.path.read_text(encoding="utf-8"),
                                   encoding="utf-8")
                except OSError:
                    pass
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # ---------- API ----------

    def add(self, text: str, kind: str = "THOUGHT", priority: str = "NORMAL",
            tags: Optional[Iterable[str]] = None, session: Optional[str] = None,
            chain_ref: str = "") -> Memory:
        kind = (kind or "THOUGHT").upper()
        priority = (priority or "NORMAL").upper()
        if kind not in KINDS:
            raise ValueError(f"Неизвестный kind: {kind}. Доступно: {KINDS}")
        if priority not in PRIORITIES:
            raise ValueError(f"Неизвестный priority: {priority}. Доступно: {PRIORITIES}")

        if tags is None:
            tags_list: list[str] = []
        elif isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        else:
            tags_list = [str(t).strip() for t in tags if str(t).strip()]

        mem = Memory(
            text=text.strip(), kind=kind, priority=priority, tags=tags_list,
            session=session or _current_session(), ts=_now_iso(),
            chain_ref=chain_ref,
        )
        mem.hash = mem.compute_hash()

        for existing in self._memories:
            if existing.hash == mem.hash:
                return existing  # дедуп

        self._memories.append(mem)
        self._save()
        return mem

    def all(self) -> list[Memory]:
        return list(self._memories)

    def count(self) -> int:
        return len(self._memories)

    def sessions(self) -> list[str]:
        seen: list[str] = []
        for m in self._memories:
            if m.session and m.session not in seen:
                seen.append(m.session)
        return seen

    def latest(self, n: int = 20) -> list[Memory]:
        return list(reversed(self._memories[-n:]))

    def critical(self, n: int = 10) -> list[Memory]:
        crit = [m for m in self._memories if m.priority in ("CRITICAL", "IMPORTANT")]
        crit.sort(key=lambda m: PRIORITY_ORDER.get(m.priority, 99))
        return crit[:n]

    def by_tag(self, tag: str) -> list[Memory]:
        return [m for m in self._memories if tag in m.tags]

    def by_kind(self, kind: str) -> list[Memory]:
        k = kind.upper()
        return [m for m in self._memories if m.kind == k]

    # ---------- Рендер ----------

    def _fmt(self, m: Memory) -> str:
        ke = KIND_EMOJI.get(m.kind, "•")
        pe = PRIORITY_EMOJI.get(m.priority, "•")
        tags = f" `#{'` `#'.join(m.tags)}`" if m.tags else ""
        return (
            f"- {ke} **[{m.kind}]** {pe} `{m.priority}` — {m.text}\n"
            f"  <sub>{m.ts} · session `{m.session}` · `{m.hash[:10]}`{tags}</sub>"
        )

    def brief(self, max_critical: int = 10, max_latest: int = 20) -> str:
        lines: list[str] = []
        lines.append("## 🧠 AI Memory — бриф")
        lines.append("")
        lines.append(f"_Воспоминаний всего: {self.count()}_")
        lines.append("")

        starts = [m for m in self._memories if m.kind == "SESSION_START"]
        if starts:
            lines.append("### 🚀 Сессии")
            for m in starts[-5:][::-1]:
                lines.append(self._fmt(m))
            lines.append("")

        crit = self.critical(max_critical)
        if crit:
            lines.append(f"### 🔴 Критично и важно (топ-{len(crit)})")
            for m in crit:
                lines.append(self._fmt(m))
            lines.append("")

        latest = self.latest(max_latest)
        if latest:
            lines.append(f"### 🕒 Последние {len(latest)}")
            for m in latest:
                lines.append(self._fmt(m))
            lines.append("")

        if not self._memories:
            lines.append("_Память пуста. Запиши первое воспоминание:_")
            lines.append("")
            lines.append("```")
            lines.append('python scripts/ai_remember.py "Начало сессии" '
                         '--kind=SESSION_START --priority=NORMAL')
            lines.append("```")

        return "\n".join(lines)

    def stats(self) -> dict:
        by_kind: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for m in self._memories:
            by_kind[m.kind] = by_kind.get(m.kind, 0) + 1
            by_priority[m.priority] = by_priority.get(m.priority, 0) + 1
        return {
            "total": len(self._memories),
            "sessions": len(self.sessions()),
            "by_kind": by_kind,
            "by_priority": by_priority,
        }