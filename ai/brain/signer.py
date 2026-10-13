"""
Подписанты Brain.

Идея: LLM формулирует намерение, но НИКОГДА не видит приватный ключ.
Ключ читается только в confirm_and_send (safe_send) и только после y/N.
Для остальных write-операций — только confirm_action (y/N без ключа).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from core.wallet import Wallet  # type: ignore
    _WALLET_OK = True
except Exception:  # noqa: BLE001
    Wallet = None  # type: ignore
    _WALLET_OK = False


class BaseSigner:
    """Интерфейс подписанта. По умолчанию — всё запрещено."""

    enabled: bool = False
    name: str = "base"

    @property
    def sender_address(self) -> str | None:
        return None

    def confirm_and_send(self, preview: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": "signer не настроен"}

    def confirm_action(self, preview: dict[str, Any], action_type: str) -> bool:
        return False


class NullSigner(BaseSigner):
    """Ничего не отправляет и не подтверждает. Безопасный дефолт."""

    enabled = False
    name = "null"

    def confirm_and_send(self, preview: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": False,
            "error": (
                "Отправка через этот канал отключена. "
                "Используй CLI: aix brain chat --wallet <имя> "
                "или aix brain send <кошелёк> <получатель> <сумма>"
            ),
        }

    def confirm_action(self, preview: dict[str, Any], action_type: str) -> bool:
        return False


class CLISigner(BaseSigner):
    """Интерактивный подписант для терминала.

    Каждая транзакция/действие требует явного y/yes.
    Приватный ключ читается ТОЛЬКО в confirm_and_send (safe_send).
    """

    enabled = True

    _ACTION_TITLES: dict[str, str] = {
        "gift_create":       "СОЗДАНИЕ ПОДАРКА",
        "timelock_create":   "СОЗДАНИЕ КАПСУЛЫ ВРЕМЕНИ",
        "swap_execute":      "ОБМЕН ТОКЕНОВ",
        "sbt_award":         "ВЫДАЧА МЕДАЛИ",
        "id_register":       "РЕГИСТРАЦИЯ AIX-ID",
    }

    # Ключи preview, которые НЕ печатаем в confirm_action —
    # они уже отображаются в шапке или дублируются.
    _PREVIEW_SKIP_KEYS = {
        "Кошелёк", "Кошелёк (issuer)", "Sender",
        "Кошелёк (sender)", "Issuer",
    }

    def __init__(self, wallet_name: str, node_url: str = "http://127.0.0.1:8010"):
        self.wallet_name = wallet_name
        self.node_url = node_url.rstrip("/")
        self.name = f"cli:{wallet_name}"

    @property
    def sender_address(self) -> str | None:
        if not _WALLET_OK:
            return None
        try:
            return Wallet.load(self.wallet_name).address
        except Exception:  # noqa: BLE001
            return None

    # ---------- safe_send (с подписью) ----------

    def confirm_and_send(self, preview: dict[str, Any]) -> dict[str, Any]:
        if not _WALLET_OK:
            return {"ok": False, "error": "core.wallet недоступен"}
        if not Wallet.exists(self.wallet_name):
            return {"ok": False, "error": f"Кошелёк '{self.wallet_name}' не найден"}

        print()
        print("┌─── ПОДТВЕРЖДЕНИЕ ОТПРАВКИ ─────────────────────────")
        print(f"│ От:     {self.wallet_name} ({self.sender_address})")
        print(f"│ Кому:   {preview.get('recipient_label') or preview.get('recipient')}")
        print(f"│ Адрес:  {preview.get('recipient')}")
        print(f"│ Сумма:  {preview.get('amount_aix')} AIX")
        msg = preview.get("message") or ""
        if msg:
            print(f"│ Msg:    {msg}")
        bb = preview.get("balance_before_aix")
        ba = preview.get("balance_after_aix")
        if bb is not None and ba is not None:
            print(f"│ Баланс: {bb} → {ba} AIX")
        print("└────────────────────────────────────────────────────")

        if not self._ask_yn("Отправить?"):
            return {"ok": False, "cancelled": True, "error": "отменено пользователем"}

        w = Wallet.load(self.wallet_name)
        payload = {
            "sender": w.address,
            "recipient": preview.get("recipient"),
            "amount": 0,
            "amount_aix": preview.get("amount_aix"),
            "private_key": w.private_key,
            "message": preview.get("message") or "",
        }
        try:
            r = requests.post(f"{self.node_url}/send", json=payload, timeout=15)
        except requests.RequestException as e:
            return {"ok": False, "error": f"Сеть: {e}"}

        if r.status_code != 200:
            try:
                data = r.json()
                detail = data.get("detail") or data.get("error") or str(data)
            except Exception:  # noqa: BLE001
                detail = (r.text or "").strip() or f"HTTP {r.status_code}"
            return {"ok": False, "error": f"Нода отказала: {detail}"}

        data = r.json()
        return {
            "ok": True,
            "status": "sent",
            "tx_id": data.get("tx_id"),
            "broadcast_to_peers": data.get("broadcast_to_peers", 0),
            "mempool_size": data.get("mempool_size", 0),
        }

    # ---------- generic action (без подписи) ----------

    def confirm_action(self, preview: dict[str, Any], action_type: str) -> bool:
        if not _WALLET_OK:
            return False
        if not Wallet.exists(self.wallet_name):
            return False

        title = self._ACTION_TITLES.get(action_type, "ПОДТВЕРЖДЕНИЕ")
        bar = "─" * max(10, 55 - len(title))
        print()
        print(f"┌─── {title} {bar}")
        print(f"│ Кошелёк: {self.wallet_name} ({self.sender_address})")
        for k, v in preview.items():
            if k in self._PREVIEW_SKIP_KEYS:
                continue
            if v is None or v == "":
                continue
            print(f"│ {k}: {v}")
        print(f"└{'─' * 55}")

        return self._ask_yn("Подтвердить?")

    def _ask_yn(self, prompt: str) -> bool:
        try:
            answer = input(f"{prompt} [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        return answer in ("y", "yes", "д", "да")