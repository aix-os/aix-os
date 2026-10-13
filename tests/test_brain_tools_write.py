"""
Тесты write-tools Brain: gift_create, timelock_create, swap_execute,
sbt_award, id_register.

Проверяем главное:
- Без signer'а — отказ.
- С signer'ом — confirm_action вызывается, POST идёт.
- При отмене y/N — POST НЕ идёт.
- Приватный ключ не участвует.
"""

from __future__ import annotations

from typing import Any

from ai.brain.signer import BaseSigner, NullSigner
from ai.brain.tools import BrainTools


AIX_ALICE = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
AIX_BOB = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"


class CountingSigner(BaseSigner):
    enabled = True
    name = "counting"

    def __init__(self, confirm: bool = True, sender: str = AIX_ALICE):
        self.confirm = confirm
        self._sender = sender
        self.calls: list[str] = []

    @property
    def sender_address(self):
        return self._sender

    def confirm_action(self, preview: dict[str, Any], action_type: str) -> bool:
        self.calls.append(action_type)
        return self.confirm


class PostRecorder(BrainTools):
    """BrainTools с перехваченными _get/_post — записывает вызовы."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[str] = []

    def _post(self, path: str, body: dict, timeout: int = 15) -> dict:
        self.posts.append((path, body))
        # Ответы под разные эндпоинты
        if path.endswith("/swap/quote"):
            return {"ok": True, "data": {
                "from_token": body.get("from_token"),
                "to_token": "AIX-SIM",
                "amount_in_aix": body.get("amount_in_aix"),
                "amount_out_aix": 99.0,
                "execution_price": 0.99,
                "slippage_percent": 0.4,
            }}
        if path.endswith("/gift/create"):
            return {"ok": True, "data": {"status": "created", "code": "GIFT1"}}
        if path.endswith("/timelock/create"):
            return {"ok": True, "data": {"status": "created", "id": "LOCK1"}}
        if path.endswith("/swap/execute"):
            return {"ok": True, "data": {"status": "ok", "amount_out_aix": 99.0}}
        if path.endswith("/sbt/award"):
            return {"ok": True, "data": {"status": "awarded", "medal_id": body.get("medal_id")}}
        if path.endswith("/id/register"):
            return {"ok": True, "data": {"status": "registered", "name": body.get("name")}}
        return {"ok": False, "error": "unmocked"}

    def _get(self, path: str, params=None) -> dict:
        self.gets.append(path)
        if "/id/resolve/" in path:
            # Все имена кроме bob резолвим в alice, чтобы упростить тесты
            if "bob" in path:
                return {"ok": True, "data": {"address": AIX_BOB}}
            return {"ok": True, "data": {"address": AIX_ALICE}}
        if "/balance/" in path:
            return {"ok": True, "data": {"available_aix": 1000.0}}
        return {"ok": False, "error": "unmocked"}


# ---------- gift_create ----------

def test_gift_create_posts_correctly():
    signer = CountingSigner(confirm=True)
    t = PostRecorder(signer=signer)
    r = t.gift_create(5.0, ttl_days=14, message="hi")
    assert r["ok"] is True
    assert any("/gift/create" in p for p, _ in t.posts)
    path, body = next(p for p in t.posts if "/gift/create" in p[0])
    assert body["sender"] == AIX_ALICE
    assert body["amount_aix"] == 5.0
    assert body["ttl_days"] == 14
    assert signer.calls == ["gift_create"]


def test_gift_create_cancel_blocks_post():
    signer = CountingSigner(confirm=False)
    t = PostRecorder(signer=signer)
    r = t.gift_create(5.0)
    assert r["ok"] is False
    assert r["cancelled"] is True
    assert not any("/gift/create" in p for p, _ in t.posts)
    assert signer.calls == ["gift_create"]


def test_gift_create_requires_signer():
    t = PostRecorder(signer=NullSigner())
    r = t.gift_create(5.0)
    assert r["ok"] is False
    assert not any("/gift/create" in p for p, _ in t.posts)


# ---------- timelock_create ----------

def test_timelock_create_posts_correctly():
    signer = CountingSigner(confirm=True)
    t = PostRecorder(signer=signer)
    r = t.timelock_create(10.0, "2027-01-01", message="NY")
    assert r["ok"] is True
    path, body = next(p for p in t.posts if "/timelock/create" in p[0])
    assert body["owner"] == AIX_ALICE
    assert body["until"] == "2027-01-01"
    assert signer.calls == ["timelock_create"]


def test_timelock_create_cancel_blocks_post():
    signer = CountingSigner(confirm=False)
    t = PostRecorder(signer=signer)
    r = t.timelock_create(10.0, "2027-01-01")
    assert r["ok"] is False
    assert r["cancelled"] is True
    assert not any("/timelock/create" in p for p, _ in t.posts)


def test_timelock_create_requires_until():
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    assert t.timelock_create(5.0, "")["ok"] is False
    assert signer.calls == []


# ---------- swap_execute ----------

def test_swap_execute_quotes_then_posts():
    signer = CountingSigner(confirm=True)
    t = PostRecorder(signer=signer)
    r = t.swap_execute("POOL1", "USDT-SIM", 100.0)
    assert r["ok"] is True
    # Должны быть 2 POST: /swap/quote и /swap/execute
    paths = [p for p, _ in t.posts]
    assert any("/swap/quote" in p for p in paths)
    assert any("/swap/execute" in p for p in paths)
    assert signer.calls == ["swap_execute"]


def test_swap_execute_cancel_blocks_execute():
    signer = CountingSigner(confirm=False)
    t = PostRecorder(signer=signer)
    r = t.swap_execute("POOL1", "USDT-SIM", 100.0)
    assert r["ok"] is False
    assert r["cancelled"] is True
    # quote случился (нужен для preview), но execute — нет
    paths = [p for p, _ in t.posts]
    assert any("/swap/quote" in p for p in paths)
    assert not any("/swap/execute" in p for p in paths)


def test_swap_execute_requires_signer():
    t = PostRecorder(signer=NullSigner())
    r = t.swap_execute("POOL1", "USDT-SIM", 100.0)
    assert r["ok"] is False
    assert not any("/swap/execute" in p for p, _ in t.posts)


def test_swap_execute_rejects_zero_amount():
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    assert t.swap_execute("POOL1", "USDT-SIM", 0)["ok"] is False
    assert signer.calls == []


# ---------- sbt_award ----------

def test_sbt_award_posts_correctly():
    signer = CountingSigner(confirm=True)
    t = PostRecorder(signer=signer)
    r = t.sbt_award("EARLY_BIRD", "bob", reason="первый вклад")
    assert r["ok"] is True
    path, body = next(p for p in t.posts if "/sbt/award" in p[0])
    assert body["medal_id"] == "EARLY_BIRD"
    assert body["owner"] == AIX_BOB
    assert body["issuer"] == AIX_ALICE
    assert signer.calls == ["sbt_award"]


def test_sbt_award_cancel_blocks_post():
    signer = CountingSigner(confirm=False)
    t = PostRecorder(signer=signer)
    r = t.sbt_award("EARLY_BIRD", "bob")
    assert r["ok"] is False
    assert r["cancelled"] is True
    assert not any("/sbt/award" in p for p, _ in t.posts)


def test_sbt_award_requires_signer():
    t = PostRecorder(signer=NullSigner())
    r = t.sbt_award("EARLY_BIRD", "bob")
    assert r["ok"] is False


def test_sbt_award_requires_medal():
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    assert t.sbt_award("", "bob")["ok"] is False
    assert signer.calls == []


# ---------- id_register ----------

def test_id_register_posts_correctly():
    signer = CountingSigner(confirm=True)
    t = PostRecorder(signer=signer)
    r = t.id_register("naparnik", display_name="Напарник", avatar="🚀")
    assert r["ok"] is True
    path, body = next(p for p in t.posts if "/id/register" in p[0])
    assert body["name"] == "naparnik"
    assert body["address"] == AIX_ALICE
    assert body["avatar"] == "🚀"
    assert signer.calls == ["id_register"]


def test_id_register_normalizes_at_and_case():
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    t.id_register("@Naparnik")
    path, body = next(p for p in t.posts if "/id/register" in p[0])
    assert body["name"] == "naparnik"


def test_id_register_cancel_blocks_post():
    signer = CountingSigner(confirm=False)
    t = PostRecorder(signer=signer)
    r = t.id_register("naparnik")
    assert r["ok"] is False
    assert r["cancelled"] is True
    assert not any("/id/register" in p for p, _ in t.posts)


def test_id_register_requires_name():
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    assert t.id_register("")["ok"] is False
    assert signer.calls == []


# ---------- безопасность ----------

def test_no_private_key_in_any_write_result():
    import json as _json
    signer = CountingSigner()
    t = PostRecorder(signer=signer)
    results = [
        t.gift_create(1.0),
        t.timelock_create(1.0, "2027-01-01"),
        t.swap_execute("POOL1", "USDT-SIM", 10.0),
        t.sbt_award("EARLY_BIRD", "bob"),
        t.id_register("test"),
    ]
    for r in results:
        blob = _json.dumps(r, default=str).lower()
        assert "private_key" not in blob
        assert "privkey" not in blob