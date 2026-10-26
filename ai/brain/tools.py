"""
Инструменты (tools) AIX Brain.

TOOL_SCHEMAS  — JSON-схемы (19 инструментов).
BrainTools    — исполнитель.

Ключевое: _get/_post при ошибке 4xx/5xx возвращают ТЕЛО ответа сервера
(detail/error/message), а не просто "400 Client Error". Это позволяет
LLM и пользователю видеть точную причину.
"""

from __future__ import annotations

from typing import Any, Callable

import requests

from .config import BrainConfig
from .memory_bridge import MemoryBridge
from .signer import BaseSigner, NullSigner


# ============================================================
# JSON-схемы инструментов
# ============================================================

TOOL_SCHEMAS: list[dict[str, Any]] = [
    # ---- Read: chain / wallet ----
    {"type": "function", "function": {
        "name": "chain_status",
        "description": "Состояние ноды AIX OS: высота, мемпул, пиры, версия.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "wallet_balance",
        "description": "Баланс адреса AIX. Только чтение.",
        "parameters": {"type": "object", "properties": {
            "address": {"type": "string", "description": "AIX-адрес, @id или имя кошелька"}
        }, "required": ["address"]},
    }},
    # ---- Read: DAO / PoC ----
    {"type": "function", "function": {
        "name": "dao_list",
        "description": "Список предложений DAO.",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "description": "voting|passed|executed|cancelled|all"}
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "poc_stats",
        "description": "Статистика Proof of Contribution.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    # ---- Memory ----
    {"type": "function", "function": {
        "name": "ai_memory_remember",
        "description": "Записать воспоминание в AI Memory.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"},
            "kind": {"type": "string", "description": "MILESTONE|DECISION|LEARNING|BUG_FIXED|IDEA|THOUGHT|SESSION_START|SESSION_END"},
            "priority": {"type": "string", "description": "CRITICAL|IMPORTANT|NORMAL"},
            "body": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        }, "required": ["title", "kind", "priority"]},
    }},
    {"type": "function", "function": {
        "name": "ai_memory_brief",
        "description": "Краткая сводка AI Memory.",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer"}
        }, "required": []},
    }},
    # ---- Send ----
    {"type": "function", "function": {
        "name": "preview_send",
        "description": "ПРЕДПРОСМОТР отправки AIX. Ничего не отправляет.",
        "parameters": {"type": "object", "properties": {
            "recipient": {"type": "string"},
            "amount_aix": {"type": "number"},
            "message": {"type": "string"},
        }, "required": ["recipient", "amount_aix"]},
    }},
    {"type": "function", "function": {
        "name": "safe_send",
        "description": "ОТПРАВКА AIX. Требует y/N в CLI. Ключ LLM не видит.",
        "parameters": {"type": "object", "properties": {
            "recipient": {"type": "string"},
            "amount_aix": {"type": "number"},
            "message": {"type": "string"},
        }, "required": ["recipient", "amount_aix"]},
    }},
    # ---- Gift ----
    {"type": "function", "function": {
        "name": "gift_info",
        "description": "Информация о подарочной ссылке по коду. Read-only.",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
    }},
    {"type": "function", "function": {
        "name": "gift_list",
        "description": "Список подарков, отправленных с адреса. Read-only.",
        "parameters": {"type": "object", "properties": {"address": {"type": "string"}}, "required": ["address"]},
    }},
    {"type": "function", "function": {
        "name": "gift_create",
        "description": "СОЗДАТЬ ПОДАРОЧНУЮ ССЫЛКУ. Требует y/N. Ключ не читается.",
        "parameters": {"type": "object", "properties": {
            "amount_aix": {"type": "number"},
            "ttl_days": {"type": "integer"},
            "message": {"type": "string"},
        }, "required": ["amount_aix"]},
    }},
    # ---- TimeLock ----
    {"type": "function", "function": {
        "name": "timelock_info",
        "description": "Информация о капсуле времени. Read-only.",
        "parameters": {"type": "object", "properties": {"lock_id": {"type": "string"}}, "required": ["lock_id"]},
    }},
    {"type": "function", "function": {
        "name": "timelock_list",
        "description": "Список капсул времени. Read-only.",
        "parameters": {"type": "object", "properties": {"owner": {"type": "string"}}, "required": ["owner"]},
    }},
    {"type": "function", "function": {
        "name": "timelock_create",
        "description": "СОЗДАТЬ КАПСУЛУ ВРЕМЕНИ. Требует y/N. Ключ не читается.",
        "parameters": {"type": "object", "properties": {
            "amount_aix": {"type": "number"},
            "until": {"type": "string", "description": "'2026-12-31' или '2026-12-31 23:59'"},
            "recipient": {"type": "string"},
            "message": {"type": "string"},
        }, "required": ["amount_aix", "until"]},
    }},
    # ---- Swap ----
    {"type": "function", "function": {
        "name": "swap_pools",
        "description": "Список пулов ликвидности. Read-only. ВЫЗЫВАЙ ПЕРВЫМ перед swap_quote/swap_execute.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "swap_quote",
        "description": "Котировка обмена. Ничего не меняет.",
        "parameters": {"type": "object", "properties": {
            "pool_id": {"type": "string"},
            "from_token": {"type": "string"},
            "amount_in_aix": {"type": "number"},
        }, "required": ["pool_id", "from_token", "amount_in_aix"]},
    }},
    {"type": "function", "function": {
        "name": "swap_execute",
        "description": (
            "ВЫПОЛНИТЬ ОБМЕН ТОКЕНОВ. Требует y/N. Ключ не читается. "
            "ОБЯЗАТЕЛЬНО: если не знаешь pool_id — сначала swap_pools."
        ),
        "parameters": {"type": "object", "properties": {
            "pool_id": {"type": "string"},
            "from_token": {"type": "string", "description": "USDT|AIX|BTC|ETH|SOL"},
            "amount_in_aix": {"type": "number"},
        }, "required": ["pool_id", "from_token", "amount_in_aix"]},
    }},
    # ---- SBT ----
    {"type": "function", "function": {
        "name": "sbt_award",
        "description": (
            "ВЫДАТЬ МЕДАЛЬ (SBT). Требует y/N. Issuer = кошелёк из --wallet. "
            "Ключ не читается. Проверь через /sbt/catalog, не выдали ли уже эту медаль."
        ),
        "parameters": {"type": "object", "properties": {
            "medal_id": {"type": "string", "description": "FOUNDER|EARLY_BIRD|CONTRIBUTOR|... (см. /sbt/catalog)"},
            "owner": {"type": "string", "description": "AIX-адрес, @id или имя"},
            "reason": {"type": "string"},
        }, "required": ["medal_id", "owner"]},
    }},
    # ---- AIX-ID ----
    {"type": "function", "function": {
        "name": "id_register",
        "description": (
            "ЗАРЕГИСТРИРОВАТЬ AIX-ID (@имя). Требует y/N. "
            "Адрес берётся из --wallet. Ключ не читается. "
            "Имя должно быть уникально и валидно (латиница+цифры)."
        ),
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Уникальное имя, латиница+цифры, например naparnik"},
            "display_name": {"type": "string"},
            "avatar": {"type": "string", "description": "эмодзи, например 🚀"},
            "bio": {"type": "string"},
        }, "required": ["name"]},
    }},
]


# ============================================================
# Исполнитель
# ============================================================

class BrainTools:

    def __init__(
        self,
        config: BrainConfig | None = None,
        memory: MemoryBridge | None = None,
        signer: BaseSigner | None = None,
    ):
        self.config = config or BrainConfig.from_env()
        self.memory = memory or MemoryBridge()
        self.signer = signer or NullSigner()
        self._registry: dict[str, Callable[..., dict[str, Any]]] = {
            "chain_status": self.chain_status,
            "wallet_balance": self.wallet_balance,
            "dao_list": self.dao_list,
            "poc_stats": self.poc_stats,
            "ai_memory_remember": self.ai_memory_remember,
            "ai_memory_brief": self.ai_memory_brief,
            "preview_send": self.preview_send,
            "safe_send": self.safe_send,
            "gift_info": self.gift_info,
            "gift_list": self.gift_list,
            "gift_create": self.gift_create,
            "timelock_info": self.timelock_info,
            "timelock_list": self.timelock_list,
            "timelock_create": self.timelock_create,
            "swap_pools": self.swap_pools,
            "swap_quote": self.swap_quote,
            "swap_execute": self.swap_execute,
            "sbt_award": self.sbt_award,
            "id_register": self.id_register,
        }

    def schemas(self) -> list[dict[str, Any]]:
        return TOOL_SCHEMAS

    def names(self) -> list[str]:
        return list(self._registry.keys())

    def execute(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        fn = self._registry.get(name)
        if fn is None:
            return {"ok": False, "error": f"Неизвестный инструмент: {name}"}
        try:
            return fn(**(arguments or {}))
        except TypeError as e:
            return {"ok": False, "error": f"Некорректные аргументы для {name}: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{name} упал: {e}"}

    # ---------- HTTP ----------

    def _extract_error(self, r: "requests.Response") -> str:
        """Извлечь человеческую причину ошибки из ответа сервера.

        Пытается вытащить detail / error / message / text.
        """
        try:
            data = r.json()
        except ValueError:
            data = None

        if isinstance(data, dict):
            for key in ("detail", "error", "message"):
                v = data.get(key)
                if isinstance(v, str) and v:
                    return v
            # Ещё какой-то структурированный ответ — компактно
            return str(data)[:300]
        if isinstance(data, list):
            return str(data)[:300]
        # Не JSON — просто текст
        txt = (r.text or "").strip()
        return txt[:300] if txt else f"HTTP {r.status_code}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            r = requests.get(f"{self.config.node_url}{path}", params=params, timeout=10)
        except requests.RequestException as e:
            return {"ok": False, "error": f"GET {path}: сеть: {e}"}

        if r.status_code >= 400:
            return {"ok": False,
                    "error": f"HTTP {r.status_code}: {self._extract_error(r)}"}

        try:
            return {"ok": True, "data": r.json()}
        except ValueError as e:
            return {"ok": False, "error": f"GET {path}: не JSON ({e})"}

    def _post(self, path: str, body: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
        try:
            r = requests.post(f"{self.config.node_url}{path}", json=body, timeout=timeout)
        except requests.RequestException as e:
            return {"ok": False, "error": f"POST {path}: сеть: {e}"}

        if r.status_code >= 400:
            return {"ok": False,
                    "error": f"HTTP {r.status_code}: {self._extract_error(r)}"}

        try:
            return {"ok": True, "data": r.json()}
        except ValueError as e:
            return {"ok": False, "error": f"POST {path}: не JSON ({e})"}

    # ---------- resolve ----------

    def _resolve_recipient(self, who: str) -> dict[str, Any] | None:
        who = (who or "").strip()
        if not who:
            return None

        def _valid(addr: str | None) -> bool:
            return bool(addr and addr.startswith("AIX") and len(addr) >= 30)

        if who.startswith("AIX"):
            return {"address": who, "label": who} if _valid(who) else None

        if who.startswith("phone:"):
            phone = who[6:].strip()
            r = self._post(ENDPOINTS["contacts_lookup"], {"phone": phone})
            if r.get("ok"):
                d = r["data"]
                addr = d.get("address")
                if _valid(addr):
                    return {"address": addr, "label": f"📇{d.get('aix_id') or phone}"}
            return None

        name = who.lstrip("@")
        r = self._get(ENDPOINTS["id_resolve"].format(name=name))
        if r.get("ok"):
            addr = (r["data"] or {}).get("address")
            if _valid(addr):
                return {"address": addr, "label": f"@{name}"}
        return None

    def _require_signer(self) -> dict[str, Any] | None:
        if not self.signer.enabled:
            return {"ok": False, "error": (
                "Действие отключено в этом канале. Используй CLI: "
                "aix brain chat --wallet <имя>"
            )}
        if not self.signer.sender_address:
            return {"ok": False, "error": "Кошелёк не найден"}
        return None

    def _wallet_label(self) -> str:
        name = getattr(self.signer, "wallet_name", None) or "?"
        addr = self.signer.sender_address or "?"
        return f"{name} ({addr})"

    # ---------- chain / wallet ----------

    def chain_status(self) -> dict[str, Any]:
        return self._get(ENDPOINTS["status"])

    def wallet_balance(self, address: str) -> dict[str, Any]:
        r = self._resolve_recipient(address)
        if r is None:
            return {"ok": False, "error": f"Не могу разобрать адрес: {address!r}"}
        return self._get(ENDPOINTS["balance"].format(address=r["address"]))

    # ---------- dao / poc ----------

    def dao_list(self, status: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if status and status != "all":
            params["status"] = status
        return self._get(ENDPOINTS["dao_all"], params=params or None)

    def poc_stats(self) -> dict[str, Any]:
        return self._get(ENDPOINTS["poc_stats"])

    # ---------- memory ----------

    def ai_memory_remember(self, title: str, kind: str, priority: str,
                           body: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        return self.memory.remember(title=title, kind=kind, priority=priority,
                                    body=body, tags=tags)

    def ai_memory_brief(self, limit: int = 20) -> dict[str, Any]:
        return self.memory.brief(limit=limit)

    # ---------- send ----------

    def preview_send(self, recipient: str, amount_aix: float, message: str = "") -> dict[str, Any]:
        r = self._resolve_recipient(recipient)
        if r is None:
            return {"ok": False, "error": f"Не могу разобрать получателя: {recipient!r}"}
        try:
            amount = float(amount_aix)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Сумма должна быть числом: {amount_aix!r}"}
        if amount <= 0:
            return {"ok": False, "error": "Сумма должна быть > 0"}

        sender_addr = self.signer.sender_address
        balance_before: float | None = None
        if sender_addr:
            rb = self._get(ENDPOINTS["balance"].format(address=sender_addr))
            if rb.get("ok"):
                balance_before = rb["data"].get("available_aix")

        preview = {
            "recipient": r["address"],
            "recipient_label": r["label"],
            "amount_aix": amount,
            "message": message,
            "sender": sender_addr,
            "balance_before_aix": balance_before,
            "balance_after_aix": (round(balance_before - amount, 8)
                                  if balance_before is not None else None),
        }
        if balance_before is not None and balance_before < amount:
            return {"ok": False,
                    "error": f"Недостаточно средств: доступно {balance_before} AIX",
                    "preview": preview}
        return {"ok": True, "preview": preview}

    def safe_send(self, recipient: str, amount_aix: float, message: str = "") -> dict[str, Any]:
        p = self.preview_send(recipient, amount_aix, message)
        if not p.get("ok"):
            return p
        preview = p["preview"]
        err = self._require_signer()
        if err:
            return {**err, "preview": preview}
        res = self.signer.confirm_and_send(preview)
        if res.get("ok"):
            return {"ok": True, "status": "sent",
                    "tx_id": res.get("tx_id"),
                    "broadcast_to_peers": res.get("broadcast_to_peers", 0),
                    "mempool_size": res.get("mempool_size", 0)}
        return {"ok": False,
                "error": res.get("error", "не отправлено"),
                "cancelled": res.get("cancelled", False)}

    # ---------- gift ----------

    def gift_info(self, code: str) -> dict[str, Any]:
        code = (code or "").strip()
        if not code:
            return {"ok": False, "error": "Не указан код gift-ссылки"}
        return self._get(ENDPOINTS["gift_info"].format(code=code))

    def gift_list(self, address: str) -> dict[str, Any]:
        r = self._resolve_recipient(address)
        if r is None:
            return {"ok": False, "error": f"Не могу разобрать адрес: {address!r}"}
        return self._get(ENDPOINTS["gifts_by_sender"].format(address=r["address"]))

    def gift_create(self, amount_aix: float, ttl_days: int = 30, message: str = "") -> dict[str, Any]:
        err = self._require_signer()
        if err:
            return err
        try:
            amount = float(amount_aix)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Сумма должна быть числом: {amount_aix!r}"}
        if amount <= 0:
            return {"ok": False, "error": "Сумма должна быть > 0"}
        try:
            ttl = int(ttl_days)
        except (TypeError, ValueError):
            return {"ok": False, "error": "ttl_days должен быть целым числом"}
        if ttl <= 0:
            return {"ok": False, "error": "Срок должен быть > 0"}

        sender = self.signer.sender_address
        preview = {
            "Sender": sender,
            "Сумма": f"{amount} AIX",
            "Срок жизни": f"{ttl} дней",
            "Сообщение": message or "—",
        }
        if not self.signer.confirm_action(preview, "gift_create"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}
        return self._post(ENDPOINTS["gift_create"], {
            "sender": sender, "amount_aix": amount,
            "ttl_days": ttl, "message": message,
        })

    # ---------- timelock ----------

    def timelock_info(self, lock_id: str) -> dict[str, Any]:
        lock_id = (lock_id or "").strip()
        if not lock_id:
            return {"ok": False, "error": "Не указан ID капсулы"}
        return self._get(ENDPOINTS["timelock_info"].format(lock_id=lock_id))

    def timelock_list(self, owner: str) -> dict[str, Any]:
        r = self._resolve_recipient(owner)
        if r is None:
            return {"ok": False, "error": f"Не могу разобрать владельца: {owner!r}"}
        return self._get(ENDPOINTS["timelocks_by_owner"].format(address=r["address"]))

    def timelock_create(self, amount_aix: float, until: str,
                        recipient: str = "", message: str = "") -> dict[str, Any]:
        err = self._require_signer()
        if err:
            return err
        try:
            amount = float(amount_aix)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Сумма должна быть числом: {amount_aix!r}"}
        if amount <= 0:
            return {"ok": False, "error": "Сумма должна быть > 0"}
        until = (until or "").strip()
        if not until:
            return {"ok": False, "error": "Не указана дата открытия"}

        recipient_addr = ""
        recipient_label = "—"
        if recipient:
            rr = self._resolve_recipient(recipient)
            if rr is None:
                return {"ok": False, "error": f"Не могу разобрать получателя: {recipient!r}"}
            recipient_addr = rr["address"]
            recipient_label = rr["label"]

        sender = self.signer.sender_address
        preview = {
            "Sender": sender,
            "Сумма": f"{amount} AIX",
            "Открыть": until,
            "Получатель": recipient_label,
            "Сообщение": message or "—",
        }
        if not self.signer.confirm_action(preview, "timelock_create"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}
        return self._post(ENDPOINTS["timelock_create"], {
            "owner": sender, "amount_aix": amount, "until": until,
            "recipient": recipient_addr, "message": message,
        })

    # ---------- swap ----------

    def swap_pools(self) -> dict[str, Any]:
        return self._get(ENDPOINTS["swap_pools"])

    def swap_quote(self, pool_id: str, from_token: str, amount_in_aix: float) -> dict[str, Any]:
        pool_id = (pool_id or "").strip()
        if not pool_id:
            return {"ok": False,
                    "error": "Не указан pool_id. Сначала вызови swap_pools."}
        try:
            amount = float(amount_in_aix)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Сумма должна быть числом: {amount_in_aix!r}"}
        if amount <= 0:
            return {"ok": False, "error": "Сумма должна быть > 0"}
        return self._post(ENDPOINTS["swap_quote"], {
            "pool_id": pool_id,
            "from_token": (from_token or "").upper(),
            "amount_in_aix": amount,
        })

    def swap_execute(self, pool_id: str, from_token: str, amount_in_aix: float) -> dict[str, Any]:
        err = self._require_signer()
        if err:
            return err
        pool_id = (pool_id or "").strip()
        if not pool_id:
            return {"ok": False,
                    "error": "Не указан pool_id. Сначала вызови swap_pools."}
        try:
            amount = float(amount_in_aix)
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Сумма должна быть числом: {amount_in_aix!r}"}
        if amount <= 0:
            return {"ok": False, "error": "Сумма должна быть > 0"}

        # Котировка для preview
        q = self.swap_quote(pool_id, from_token, amount)
        if not q.get("ok"):
            return {"ok": False, "error": f"Не могу посчитать котировку: {q.get('error')}"}
        qd = q["data"]

        preview = {
            "Пул": pool_id,
            "Отдаю": f"{amount} {qd.get('from_token')}",
            "Получаю": f"{qd.get('amount_out_aix')} {qd.get('to_token')}",
            "Slippage": f"{qd.get('slippage_percent')}%",
        }
        if not self.signer.confirm_action(preview, "swap_execute"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}
        return self._post(ENDPOINTS["swap_execute"], {
            "pool_id": pool_id,
            "address": self.signer.sender_address,
            "from_token": (from_token or "").upper(),
            "amount_in_aix": amount,
        })

    # ---------- sbt ----------

    def sbt_award(self, medal_id: str, owner: str, reason: str = "") -> dict[str, Any]:
        err = self._require_signer()
        if err:
            return err
        medal_id = (medal_id or "").strip().upper()
        if not medal_id:
            return {"ok": False, "error": "Не указан medal_id"}
        owner_r = self._resolve_recipient(owner)
        if owner_r is None:
            return {"ok": False, "error": f"Не могу разобрать получателя медали: {owner!r}"}

        preview = {
            "Medal": medal_id,
            "Кому": owner_r["label"],
            "Адрес": owner_r["address"],
            "Issuer": self.signer.sender_address,
            "За что": reason or "—",
        }
        if not self.signer.confirm_action(preview, "sbt_award"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}
        return self._post(ENDPOINTS["sbt_award"], {
            "medal_id": medal_id,
            "owner": owner_r["address"],
            "issuer": self.signer.sender_address,
            "reason": reason,
        })

    # ---------- aix-id ----------

    def id_register(self, name: str, display_name: str = "",
                    avatar: str = "", bio: str = "") -> dict[str, Any]:
        err = self._require_signer()
        if err:
            return err
        name = (name or "").strip().lstrip("@").lower()
        if not name:
            return {"ok": False, "error": "Не указано имя"}

        preview = {
            "AIX-ID": f"@{name}",
            "Адрес": self.signer.sender_address,
            "Отображаемое": display_name or name,
            "Аватар": avatar or "👤",
            "Био": bio or "—",
        }
        if not self.signer.confirm_action(preview, "id_register"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}
        return self._post(ENDPOINTS["id_register"], {
            "address": self.signer.sender_address,
            "name": name,
            "display_name": display_name or name,
            "avatar": avatar or "👤",
            "bio": bio,
        })


# ============================================================
# ENDPOINTS
# ============================================================

ENDPOINTS: dict[str, str] = {
    "status":             "/status",
    "balance":            "/balance/{address}",
    "dao_all":            "/dao/all",
    "poc_stats":          "/poc/stats",
    "id_resolve":         "/id/resolve/{name}",
    "id_register":        "/id/register",
    "contacts_lookup":    "/contacts/lookup",
    "gift_info":          "/gift/{code}",
    "gifts_by_sender":    "/gifts/sender/{address}",
    "gift_create":        "/gift/create",
    "timelock_info":      "/timelock/{lock_id}",
    "timelocks_by_owner": "/timelocks/owner/{address}",
    "timelock_create":    "/timelock/create",
    "swap_pools":         "/swap/pools",
    "swap_quote":         "/swap/quote",
    "swap_execute":       "/swap/execute",
    "sbt_award":          "/sbt/award",
}