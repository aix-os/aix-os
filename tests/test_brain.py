"""
Тесты AIX Brain.

Покрытие:
- схемы инструментов (19 штук)
- BrainConfig (env, with_model, дефолт qwen2.5:3b)
- _parse_tool_call (dict / JSON-строка / мусор)
- BrainTools.execute (неизвестный инструмент, кривые аргументы)
- MemoryBridge (status/remember без падения)
- BrainAgent: health, ask (без tool_calls / с tool_call / лимит итераций)

Никаких реальных HTTP-вызовов: BrainClient и BrainTools замоканы.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from ai.brain.agent import BrainAgent, MAX_TOOL_ITERATIONS
from ai.brain.client import BrainClient
from ai.brain.config import BrainConfig, DEFAULT_MODEL
from ai.brain.memory_bridge import MemoryBridge
from ai.brain.tools import BrainTools, TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# Схемы и конфиг
# ---------------------------------------------------------------------------

def test_tool_schemas_have_expected_names():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    # Базовые 8 (chain/wallet/dao/poc/memory/send)
    base = {
        "chain_status", "wallet_balance", "dao_list", "poc_stats",
        "ai_memory_remember", "ai_memory_brief",
        "preview_send", "safe_send",
    }
    assert base.issubset(names)
    # Read-only протоколы
    read_extra = {
        "gift_info", "gift_list",
        "timelock_info", "timelock_list",
        "swap_pools", "swap_quote",
    }
    assert read_extra.issubset(names)
    # Write-операции через CLI signer
    write_extra = {
        "gift_create", "timelock_create",
        "swap_execute", "sbt_award", "id_register",
    }
    assert write_extra.issubset(names)
    assert len(names) == 19


def test_tool_schemas_have_required_fields():
    for t in TOOL_SCHEMAS:
        assert t["type"] == "function"
        fn = t["function"]
        assert "name" in fn and "description" in fn and "parameters" in fn
        assert fn["parameters"]["type"] == "object"


def test_config_defaults(monkeypatch):
    for k in list(os.environ):
        if k.startswith("AIX_BRAIN_"):
            monkeypatch.delenv(k, raising=False)
    cfg = BrainConfig.from_env()
    assert cfg.base_url == "http://127.0.0.1:11434"
    assert cfg.model == DEFAULT_MODEL          # следим за дефолтом в config.py
    assert cfg.model == "qwen2.5:3b"           # явная фиксация выбора
    assert cfg.node_url == "http://127.0.0.1:8010"


def test_config_from_env_override(monkeypatch):
    monkeypatch.setenv("AIX_BRAIN_MODEL", "phi3")
    monkeypatch.setenv("AIX_BRAIN_URL", "http://10.0.0.1:11434/")
    cfg = BrainConfig.from_env()
    assert cfg.model == "phi3"
    assert cfg.base_url == "http://10.0.0.1:11434"  # трейлинг-слеш убран


def test_config_with_model_returns_new_instance():
    cfg = BrainConfig.from_env()
    cfg2 = cfg.with_model("phi3")
    assert cfg.model != cfg2.model
    assert cfg2.model == "phi3"
    assert cfg.base_url == cfg2.base_url


# ---------------------------------------------------------------------------
# _parse_tool_call
# ---------------------------------------------------------------------------

def test_parse_tool_call_dict_args():
    name, args = BrainAgent._parse_tool_call({
        "function": {"name": "wallet_balance", "arguments": {"address": "AIXabc"}}
    })
    assert name == "wallet_balance"
    assert args == {"address": "AIXabc"}


def test_parse_tool_call_string_args():
    name, args = BrainAgent._parse_tool_call({
        "function": {"name": "dao_list", "arguments": '{"status": "voting"}'}
    })
    assert name == "dao_list"
    assert args == {"status": "voting"}


def test_parse_tool_call_broken_json_returns_empty():
    name, args = BrainAgent._parse_tool_call({
        "function": {"name": "x", "arguments": "{not valid json"}
    })
    assert name == "x"
    assert args == {}


def test_parse_tool_call_empty_string_args():
    name, args = BrainAgent._parse_tool_call({
        "function": {"name": "chain_status", "arguments": ""}
    })
    assert name == "chain_status"
    assert args == {}


# ---------------------------------------------------------------------------
# BrainTools
# ---------------------------------------------------------------------------

def test_tools_unknown_name_returns_error():
    t = BrainTools()
    r = t.execute("no_such_tool", {})
    assert r["ok"] is False
    assert "Неизвестный" in r["error"]


def test_tools_wallet_balance_bad_address():
    t = BrainTools()
    r = t.wallet_balance("not-aix-address")
    assert r["ok"] is False
    # wallet_balance резолвит адрес через _resolve_recipient
    assert "разобрать" in r["error"].lower() or "AIX" in r["error"]


def test_tools_execute_never_raises_on_missing_arg():
    t = BrainTools()
    # wallet_balance требует address -> TypeError внутри, должен быть пойман
    r = t.execute("wallet_balance", None)
    assert r["ok"] is False
    assert "error" in r


def test_tools_schemas_and_names_consistent():
    t = BrainTools()
    schema_names = {s["function"]["name"] for s in t.schemas()}
    impl_names = set(t.names())
    assert schema_names == impl_names


# ---------------------------------------------------------------------------
# MemoryBridge
# ---------------------------------------------------------------------------

def test_memory_bridge_status_returns_dict():
    mb = MemoryBridge()
    st = mb.status()
    assert isinstance(st, dict)
    assert "ok" in st


def test_memory_bridge_remember_never_raises():
    mb = MemoryBridge()
    r = mb.remember("тест", "THOUGHT", "NORMAL")
    assert isinstance(r, dict)
    assert "ok" in r
    if not r["ok"]:
        assert "error" in r


# ---------------------------------------------------------------------------
# BrainAgent
# ---------------------------------------------------------------------------

def _patch_client(extract_from: type = BrainClient) -> MagicMock:
    """MagicMock для клиента с реальными статическими extract_*."""
    m = MagicMock()
    m.extract_text = extract_from.extract_text
    m.extract_tool_calls = extract_from.extract_tool_calls
    return m


def test_agent_health_returns_expected_keys():
    agent = BrainAgent()
    h = agent.health()
    for key in ("backend_available", "backend_url", "model",
                "model_installed", "models_available",
                "memory_available", "tools", "node_url",
                "signer", "signer_enabled"):
        assert key in h
    assert isinstance(h["tools"], list)
    assert "chain_status" in h["tools"]
    assert "gift_create" in h["tools"]
    assert "timelock_create" in h["tools"]
    assert "swap_execute" in h["tools"]
    assert "sbt_award" in h["tools"]
    assert "id_register" in h["tools"]
    assert len(h["tools"]) == 19


def test_agent_ask_no_tool_calls_returns_text():
    fake_client = _patch_client()
    fake_client.chat.return_value = {
        "message": {"role": "assistant", "content": "привет, напарник"}
    }
    agent = BrainAgent(client=fake_client)
    result = agent.ask("привет")
    assert result == "привет, напарник"


def test_agent_ask_with_tool_call_executes_tool():
    fake_client = _patch_client()
    call1 = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "chain_status", "arguments": {}}}
            ],
        }
    }
    call2 = {"message": {"role": "assistant", "content": "Высота 17"}}
    fake_client.chat.side_effect = [call1, call2]

    fake_tools = MagicMock()
    fake_tools.schemas.return_value = []
    fake_tools.names.return_value = ["chain_status"]
    fake_tools.execute.return_value = {"ok": True, "data": {"height": 17}}

    agent = BrainAgent(client=fake_client, tools=fake_tools)
    result = agent.ask("какая высота?")

    assert result == "Высота 17"
    fake_tools.execute.assert_called_once_with("chain_status", {})


def test_agent_ask_breaks_after_max_tool_iterations():
    """Модель бесконечно зовёт tool — выходим по лимиту."""
    fake_client = _patch_client()
    forever = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "x", "arguments": {}}}],
        }
    }
    fake_client.chat.return_value = forever

    fake_tools = MagicMock()
    fake_tools.schemas.return_value = []
    fake_tools.names.return_value = ["x"]
    fake_tools.execute.return_value = {"ok": True}

    agent = BrainAgent(client=fake_client, tools=fake_tools)
    result = agent.ask("loop")

    assert fake_client.chat.call_count == MAX_TOOL_ITERATIONS
    assert "предел" in result.lower()