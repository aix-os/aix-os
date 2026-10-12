"""AIX OS — тесты AI Memory (#AI-1)."""
import json
import pytest
from pathlib import Path

from core.protocols.ai_memory import (
    AIMemoryManager, Memory, KINDS, PRIORITIES,
)


@pytest.fixture
def tmp_memory(tmp_path):
    return AIMemoryManager(tmp_path / "ai_memory.json")


def test_empty(tmp_memory):
    assert tmp_memory.count() == 0
    assert tmp_memory.sessions() == []
    assert "Память пуста" in tmp_memory.brief()


def test_add_and_persist(tmp_path):
    path = tmp_path / "ai_memory.json"
    mgr = AIMemoryManager(path)
    m = mgr.add("Тестовое воспоминание", kind="MILESTONE", priority="IMPORTANT",
                tags="test,ai", session="s1")
    assert m.kind == "MILESTONE"
    assert m.priority == "IMPORTANT"
    assert m.tags == ["test", "ai"]
    assert m.session == "s1"
    assert m.hash

    mgr2 = AIMemoryManager(path)
    assert mgr2.count() == 1
    assert mgr2.all()[0].text == "Тестовое воспоминание"


def test_dedup(tmp_memory):
    m1 = tmp_memory.add("Одно и то же", kind="THOUGHT", priority="NORMAL")
    m2 = tmp_memory.add("Одно и то же", kind="THOUGHT", priority="NORMAL")
    assert m1.hash == m2.hash
    assert tmp_memory.count() == 1


def test_invalid_kind(tmp_memory):
    with pytest.raises(ValueError):
        tmp_memory.add("x", kind="UNKNOWN")


def test_invalid_priority(tmp_memory):
    with pytest.raises(ValueError):
        tmp_memory.add("x", priority="UNKNOWN")


def test_critical_and_latest(tmp_memory):
    tmp_memory.add("A", priority="NORMAL")
    tmp_memory.add("B", priority="CRITICAL")
    tmp_memory.add("C", priority="IMPORTANT")
    tmp_memory.add("D", priority="CRITICAL")
    crit = tmp_memory.critical(10)
    assert len(crit) == 3
    latest = tmp_memory.latest(2)
    assert len(latest) == 2
    assert latest[0].text == "D"


def test_by_tag(tmp_memory):
    tmp_memory.add("A", tags="mempool,chain")
    tmp_memory.add("B", tags="poc")
    assert len(tmp_memory.by_tag("mempool")) == 1
    assert len(tmp_memory.by_tag("nonexistent")) == 0


def test_by_kind(tmp_memory):
    tmp_memory.add("A", kind="BUG_FIXED")
    tmp_memory.add("B", kind="MILESTONE")
    assert len(tmp_memory.by_kind("BUG_FIXED")) == 1


def test_brief_contains_memory(tmp_memory):
    tmp_memory.add("Уникальное событие 12345", kind="MILESTONE", priority="CRITICAL")
    brief = tmp_memory.brief()
    assert "Уникальное событие 12345" in brief
    assert "MILESTONE" in brief


def test_corrupted_file_recovery(tmp_path):
    path = tmp_path / "ai_memory.json"
    path.write_text("{ broken json", encoding="utf-8")
    mgr = AIMemoryManager(path)
    assert mgr.count() == 0


def test_sessions(tmp_memory):
    tmp_memory.add("A", session="s1")
    tmp_memory.add("B", session="s1")
    tmp_memory.add("C", session="s2")
    assert tmp_memory.sessions() == ["s1", "s2"]