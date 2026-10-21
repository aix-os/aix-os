"""AIX OS — Fiat On-Ramp (Покупка AIX за рубли)."""
import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import config

# Курс (временно жестко, потом можно брать с API ЦБ)
RUB_PER_USD = 90.0
AIX_PRICE_USD = 100.0
AIX_PRICE_RUB = AIX_PRICE_USD * RUB_PER_USD  # 9000 рублей за 1 AIX

@dataclass
class FiatInvoice:
    id: str
    address: str
    amount_rub: float
    amount_aix: float
    status: str  # pending, paid, cancelled
    created_at: float
    paid_at: float = 0.0
    tx_id: str = ""

class FiatManager:
    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.invoices: dict[str, FiatInvoice] = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for item in data.get("invoices", []):
                inv = FiatInvoice(**item)
                self.invoices[inv.id] = inv
        except Exception as e:
            print(f"WARN: fiat load error: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"invoices": [asdict(i) for i in self.invoices.values()]}
        self.storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_invoice(self, address: str, amount_rub: float) -> FiatInvoice:
        inv_id = str(uuid.uuid4())
        amount_aix = amount_rub / AIX_PRICE_RUB
        
        inv = FiatInvoice(
            id=inv_id,
            address=address,
            amount_rub=amount_rub,
            amount_aix=amount_aix,
            status="pending",
            created_at=time.time()
        )
        self.invoices[inv_id] = inv
        self._save()
        return inv

    def mark_paid(self, inv_id: str, blockchain) -> bool:
        inv = self.invoices.get(inv_id)
        if not inv or inv.status == "paid":
            return False
        
        # Начисляем AIX как транзакцию от FAUCET (или FIAT-POOL)
        from core.transaction import Transaction
        amount_raw = int(inv.amount_aix * config.SATOSHI)
        
        tx = Transaction(
            sender="FAUCET",  # Используем системный адрес для простоты
            recipient=inv.address,
            amount=amount_raw,
            message=f"Fiat purchase: {inv.amount_rub} RUB"
        )
        ok, msg = blockchain.mempool.add(tx)
        if not ok:
            print(f"FIAT ERROR: {msg}")
            return False
            
        inv.status = "paid"
        inv.paid_at = time.time()
        inv.tx_id = tx.tx_id()
        self._save()
        return True
