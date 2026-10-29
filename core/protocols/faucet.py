"""AIX OS — Faucet (системный кран)."""
import json, time
from pathlib import Path
from typing import Optional
from core.transaction import Transaction
import config

FAUCET_AMOUNT_AIX = 1
COOLDOWN_IP_HOURS = 24
HOURLY_LIMIT = 100

class FaucetManager:
    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.blockchain = blockchain
        self.entries = []
        self._load()

    def _load(self):
        if not self.storage_path.exists(): return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.entries = data.get("entries", [])
        except Exception: pass

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"entries": self.entries}, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    def can_claim(self, address: str, ip: str) -> tuple[bool, str]:
        if not address.startswith("AIX") or len(address) < 30:
            return False, "Невалидный AIX-адрес"
        for e in self.entries:
            if e["address"] == address:
                return False, "Этот адрес уже получал AIX"
            if e.get("ip") == ip and time.time() - (e.get("time") or e.get("ts") or 0) < COOLDOWN_IP_HOURS * 3600:
                return False, f"Этот IP получал AIX менее {COOLDOWN_IP_HOURS} часов назад"
        recent = [e for e in self.entries if time.time() - (e.get("time") or e.get("ts") or 0) < 3600]
        if len(recent) >= HOURLY_LIMIT:
            return False, "Достигнут часовой лимит выдачи"
        return True, "OK"

    def claim(self, address: str, ip: str) -> tuple[bool, str, Optional[str]]:
        ok, msg = self.can_claim(address, ip)
        if not ok: return False, msg, None
        if not self.blockchain: return False, "Нет блокчейна", None

        tx = Transaction(
            sender="FAUCET",
            recipient=address,
            amount=int(FAUCET_AMOUNT_AIX * config.SATOSHI),
            fee=0,
            message="Faucet reward"
        )
        ok, msg = tx.is_valid()
        if not ok: return False, f"Ошибка: {msg}", None
        ok, msg = self.blockchain.mempool.add(tx)
        if not ok: return False, f"Mempool: {msg}", None

        self.entries.append({"address": address, "ip": ip, "time": time.time(), "amount_aix": FAUCET_AMOUNT_AIX, "tx_id": tx.tx_id()})
        self._save()
        return True, "sent", tx.tx_id()

    def stats(self) -> dict:
        return {
            "treasury": "FAUCET (системный)",
            "amount_per_claim_aix": FAUCET_AMOUNT_AIX,
            "cooldown_ip_hours": COOLDOWN_IP_HOURS,
            "hourly_limit": HOURLY_LIMIT,
            "total_claims": len(self.entries),
            "total_sent_aix": sum(e["amount_aix"] for e in self.entries),
            "claims_last_hour": len([e for e in self.entries if time.time() - (e.get("time") or e.get("ts") or 0) < 3600]),
            "claims_last_24h": len([e for e in self.entries if time.time() - (e.get("time") or e.get("ts") or 0) < 86400]),
        }
