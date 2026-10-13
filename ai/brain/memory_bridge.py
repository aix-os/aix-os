"""
Мост между Brain и AI Memory (#AI-1).

В отличие от остальных инструментов, память зовём НАПРЯМУЮ через
core.protocols.ai_memory, а не через HTTP — это быстрее, не зависит
от живости ноды и не гоняет данные по сети.

Импорт защищён: если ai_memory недоступен (упал, не в sys.path),
мост деградирует и возвращает {ok: False, error: ...} вместо исключения.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Гарантируем, что корень проекта в sys.path — чтобы core.protocols нашёлся,
# даже если Brain дёрнули из нестандартного места.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from core.protocols import ai_memory as _aimem  # type: ignore
    _AIMEM_OK = True
except Exception as _e:  # noqa: BLE001
    _aimem = None
    _AIMEM_OK = False
    _AIMEM_ERR = str(_e)


class MemoryBridge:
    """Тонкая обёртка над ai_memory. Все методы возвращают dict, не бросают."""

    def available(self) -> bool:
        return _AIMEM_OK

    def status(self) -> dict[str, Any]:
        if not _AIMEM_OK:
            return {"ok": False, "error": f"ai_memory недоступен: {_AIMEM_ERR}"}
        try:
            stats = _aimem.stats() if hasattr(_aimem, "stats") else {}
            return {"ok": True, "stats": stats}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def remember(
        self,
        title: str,
        kind: str = "MILESTONE",
        priority: str = "NORMAL",
        body: str = "",
        tags: list[str] | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        """Записать воспоминание. Сигнатура гибкая — подгоним под ai_memory."""
        if not _AIMEM_OK:
            return {"ok": False, "error": f"ai_memory недоступен: {_AIMEM_ERR}"}
        try:
            # ai_memory.remember(...) — точная сигнатура в проекте;
            # используем kwargs, лишние отфильтруем по факту.
            fn = getattr(_aimem, "remember", None)
            if fn is None:
                return {"ok": False, "error": "ai_memory.remember не найден"}

            kwargs: dict[str, Any] = {
                "title": title,
                "kind": kind,
                "priority": priority,
            }
            if body:
                kwargs["body"] = body
            if tags:
                kwargs["tags"] = tags
            if session:
                kwargs["session"] = session

            # Пробуем с полным набором, при TypeError — урезаем до title/kind/priority.
            try:
                rec = fn(**kwargs)
            except TypeError:
                rec = fn(title=title, kind=kind, priority=priority)

            return {"ok": True, "record": rec}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def brief(self, limit: int = 20) -> dict[str, Any]:
        """Краткая сводка памяти (для контекста агента)."""
        if not _AIMEM_OK:
            return {"ok": False, "error": f"ai_memory недоступен: {_AIMEM_ERR}"}
        try:
            fn = getattr(_aimem, "brief", None)
            if fn is None:
                return {"ok": False, "error": "ai_memory.brief не найден"}
            try:
                data = fn(limit=limit)
            except TypeError:
                data = fn()
            return {"ok": True, "brief": data}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def list_recent(self, limit: int = 20) -> dict[str, Any]:
        if not _AIMEM_OK:
            return {"ok": False, "error": f"ai_memory недоступен: {_AIMEM_ERR}"}
        try:
            fn = getattr(_aimem, "list_recent", None) or getattr(_aimem, "list", None)
            if fn is None:
                return {"ok": False, "error": "ai_memory.list* не найден"}
            try:
                data = fn(limit=limit)
            except TypeError:
                data = fn()
            return {"ok": True, "records": data}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}