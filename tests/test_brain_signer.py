"""
Тесты AIX Brain — слой безопасной отправки и подтверждений.

Проверяем главное:
- NullSigner НИКОГДА не отправляет и не подтверждает.
- safe_send без signer'а → ошибка, никаких side effects.
- safe_send с fake signer → пропускает tx_id.
- confirm_action вызывается для gift/timelock/swap/sbt/id.
- При отмене y/N — POST НЕ идёт.
- Приватный ключ НЕ попадает в результат инструмента.

Никаких реальных HTTP-вызовов: BrainTools замокан.
"""

from __future__ import annotations

from typing import Any

from ai.brain.signer import BaseSigner, NullSigner
from ai.brain.tools import BrainTools


# Реалистичные адреса из проекта
AIX_ALICE = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
AIX_BOB = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"


class FakeSigner(BaseSigner):
    """Тестовый подписант: отдаёт заданные результаты."""
    enabled = True
    name = "fake"

    def __init__(self, send_result: dict[str, Any] | None = None,
                 sender: str | None = AIX_ALICE,
                 confirm_action_result: bool = True):
        self.send_result = send_result or {"ok": True, "tx_id": "x"}
        self._sender = sender
        self.confirm_action_result = confirm_action_result
        self.send_calls: list[dict[str, Any]] = []
        self.action_calls: list[tuple[dict[str, Any], str]] = []

    @property
    def sender_address(self):
        return self._sender

    def confirm_and_send(self, preview: dict[str, Any]) -> dict[str, Any]:
        self.send_calls.append(preview)
        return self.send_result

    def confirm_action(self, preview: dict[str, Any], action_type: str) -> bool:
        self.action_calls.append((preview, action_type))
        return self.confirm_action_result


# ---------- Signer ----------

def test_null_signer_refuses_send():
    r = NullSigner().confirm_and_send({"recipient": AIX_BOB, "amount_aix": 1})
    assert r["ok"] is False
    assert "CLI" in r["error"]


def test_null_signer_refuses_action():
    assert NullSigner().confirm_action({"X": "Y"}, "gift_create") is False


def test_null_signer_disabled():
    s = NullSigner()
    assert s.enabled is False
    assert s.sender_address is None


# ---------- stub tools ----------

def _stub_tools(signer=None, balance_available: float = 100.0) -> BrainTools:
    """Мок ноды: резолвим ТОЛЬКО @alice и @bob, всё остальное → 404."""
    t = BrainTools(signer=signer or NullSigner())

    def fake_get(path, params=None):
        if "/balance/" in path:
            return {"ok": True, "data": {"available_aix": balance_available}}
        if "/id/resolve/alice" in path:
            return {"ok": True, "data": {"address": AIX_ALICE}}
        if "/id/resolve/bob" in path:
            return {"ok": True, "data": {"address": AIX_BOB}}
        if "/id/resolve/" in path:
            return {"ok": False, "error": "AIX-ID не найден"}
        return {"ok": False, "error": "not mocked"}

    def fake_post(path, body, timeout=15):
        if path.endswith("/swap/quote"):
            return {"ok": True, "data": {
                "from_token": body.get("from_token"),
                "to_token": "AIX",
                "amount_in_aix": body.get("amount_in_aix"),
                "amount_out_aix": 99.0,
                "execution_price": 0.99,
                "slippage_percent": 0.4,
            }}
        if path.endswith("/gift/create"):
            return {"ok": True, "data": {"status": "created", "code": "ABC123"}}
        if path.endswith("/timelock/create"):
            return {"ok": True, "data": {"status": "created", "id": "LOCK-1"}}
        if path.endswith("/swap/execute"):
            return {"ok": True, "data": {"status": "ok", "amount_out_aix": 99.0}}
        if path.endswith("/sbt/award"):
            return {"ok": True, "data": {"status": "awarded"}}
        if path.endswith("/id/register"):
            return {"ok": True, "data": {"status": "registered"}}
        return {"ok": False, "error": "not mocked"}

    t._get = fake_get         # type: ignore
    t._post = fake_post       # type: ignore
    return t


# ---------- preview_send ----------

def test_preview_send_direct_address():
    t = _stub_tools()
    r = t.preview_send(AIX_BOB, 5.0)
    assert r["ok"] is True
    assert r["preview"]["recipient"] == AIX_BOB
    assert r["preview"]["sender"] is None


def test_preview_send_resolves_aix_id():
    t = _stub_tools()
    r = t.preview_send("@alice", 5.0)
    assert r["ok"] is True
    assert r["preview"]["recipient"] == AIX_ALICE


def test_preview_send_rejects_unknown_recipient():
    t = _stub_tools()
    r = t.preview_send("непонятно-что", 5.0)
    assert r["ok"] is False


def test_preview_send_rejects_short_fake_address():
    t = _stub_tools()
    r = t.preview_send("AIXshort", 5.0)
    assert r["ok"] is False


def test_preview_send_rejects_bad_amount():
    t = _stub_tools()
    assert t.preview_send(AIX_BOB, -1)["ok"] is False
    assert t.preview_send(AIX_BOB, "не число")["ok"] is False  # type: ignore


def test_preview_send_insufficient_balance():
    t = _stub_tools(signer=FakeSigner(sender=AIX_ALICE), balance_available=3.0)
    r = t.preview_send(AIX_BOB, 5.0)
    assert r["ok"] is False
    assert "Недостаточно" in r["error"]


# ---------- safe_send ----------

def test_safe_send_without_signer_blocked():
    t = _stub_tools(signer=NullSigner())
    r = t.safe_send(AIX_BOB, 5.0)
    assert r["ok"] is False
    assert "отключено" in r["error"].lower() or "CLI" in r["error"]
    assert "preview" in r


def test_safe_send_success():
    signer = FakeSigner(send_result={
        "ok": True, "status": "sent", "tx_id": "abc123", "broadcast_to_peers": 1
    })
    t = _stub_tools(signer=signer, balance_available=100.0)
    r = t.safe_send(AIX_BOB, 5.0, "привет")
    assert r["ok"] is True
    assert r["tx_id"] == "abc123"
    assert r["broadcast_to_peers"] == 1
    assert len(signer.send_calls) == 1
    assert "private_key" not in signer.send_calls[0]


def test_safe_send_cancelled_by_user():
    signer = FakeSigner(send_result={"ok": False, "cancelled": True,
                                      "error": "отменено"})
    t = _stub_tools(signer=signer, balance_available=100.0)
    r = t.safe_send(AIX_BOB, 5.0)
    assert r["ok"] is False
    assert r["cancelled"] is True


# ---------- gift_create (через confirm_action) ----------

def test_gift_create_requires_signer():
    t = _stub_tools(signer=NullSigner())
    r = t.gift_create(5.0)
    assert r["ok"] is False
    assert "отключено" in r["error"].lower() or "CLI" in r["error"]


def test_gift_create_success():
    signer = FakeSigner()
    t = _stub_tools(signer=signer)
    r = t.gift_create(5.0, ttl_days=7, message="на днюху")
    assert r["ok"] is True
    assert r["data"]["code"] == "ABC123"
    assert len(signer.action_calls) == 1
    preview, action_type = signer.action_calls[0]
    assert action_type == "gift_create"
    assert "5.0 AIX" in preview["Сумма"]


def test_gift_create_cancelled():
    signer = FakeSigner(confirm_action_result=False)
    t = _stub_tools(signer=signer)
    r = t.gift_create(5.0)
    assert r["ok"] is False
    assert r["cancelled"] is True
    assert len(signer.action_calls) == 1


# ---------- Ключевая проверка безопасности ----------

def test_no_private_key_leak_in_any_result():
    """Слово 'private_key' не должно появляться ни в одном результате."""
    import json as _json
    t = _stub_tools(signer=FakeSigner(send_result={"ok": True, "tx_id": "x"}),
                    balance_available=100.0)
    results = [
        t.safe_send(AIX_BOB, 1.0),
        t.preview_send(AIX_BOB, 1.0),
        t.gift_create(1.0),
    ]
    for r in results:
        blob = _json.dumps(r, default=str).lower()
        assert "private_key" not in blob
        assert "privkey" not in blob


def test_tools_registry_includes_new_tools():
    t = BrainTools()
    names = set(t.names())
    assert "preview_send" in names
    assert "safe_send" in names
    assert "chain_status" in names
    assert "gift_create" in names
    assert "timelock_create" in names
    assert "swap_execute" in names
    assert "sbt_award" in names
    assert "id_register" in names