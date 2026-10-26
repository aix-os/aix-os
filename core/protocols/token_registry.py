"""AIX OS — Реестр токенов (Империя 2.0).

Любой может зарегистрировать свой токен внутри AIX OS.
При регистрации создаётся пул TOKEN/AIX в Swap.
"""
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import config
from core.oracle import get_usd_price, AIX_USD

# Базовые токены, которые уже есть в системе (не требуют регистрации)
BASE_TOKENS = {
    "AIX": {"name": "AIX OS", "emoji": "⚡", "decimals": 18, "creator": "system"},
}


@dataclass
class TokenRecord:
    symbol: str
    name: str
    creator: str
    total_supply: int
    decimals: int = 18
    emoji: str = "🪙"
    created_at: float = 0.0
    description: str = ""
    initial_pool_aix: int = 0
    initial_pool_token: int = 0
    usd_price: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenRecord":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)


class TokenRegistry:
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.tokens: dict[str, TokenRecord] = {}
        self._load()

    def _load(self):
        for sym, info in BASE_TOKENS.items():
            self.tokens[sym] = TokenRecord(
                symbol=sym, name=info["name"], creator=info["creator"],
                total_supply=0, decimals=info["decimals"], emoji=info["emoji"],
            )
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for item in data.get("tokens", []):
                    t = TokenRecord.from_dict(item)
                    self.tokens[t.symbol] = t
            except Exception as e:
                print(f"WARN: token_registry load: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        custom = [t for sym, t in self.tokens.items() if sym not in BASE_TOKENS]
        data = {"tokens": [t.to_dict() for t in custom]}
        self.storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def register(self, creator: str, symbol: str, name: str,
                 total_supply: int, emoji: str = "🪙",
                 description: str = "",
                 initial_pool_aix: int = 0,
                 initial_pool_token: int = 0,
                 usd_price: float = 0.0) -> tuple:
        symbol = symbol.upper().strip()
        if not symbol or len(symbol) > 10:
            return False, "Тикер: 1..10 символов"
        if symbol in self.tokens:
            return False, f"Токен {symbol} уже существует"
        if total_supply <= 0:
            return False, "Эмиссия должна быть > 0"
        if not name or len(name) > 50:
            return False, "Название: 1..50 символов"
        if initial_pool_aix < 0 or initial_pool_token < 0:
            return False, "Ликвидность не может быть < 0"
        if initial_pool_token > total_supply:
            return False, "Ликвидность токена больше эмиссии"
        # --- Цена токена ---
        sym = symbol.upper()
        if usd_price <= 0:
            usd_price = get_usd_price(sym) or 0.0
        if usd_price <= 0:
            return False, f"Не знаю USD-цену для '{sym}'. Укажи вручную."
        usd_price = float(usd_price)

        # --- Авто-расчёт второй стороны ликвидности ---
        aix_usd = float(AIX_USD)
        if initial_pool_aix > 0 and initial_pool_token == 0:
            initial_pool_token = int(round(initial_pool_aix * aix_usd / usd_price))
        elif initial_pool_token > 0 and initial_pool_aix == 0:
            initial_pool_aix = int(round(initial_pool_token * usd_price / aix_usd))
        if initial_pool_token <= 0 or initial_pool_aix <= 0:
            return False, "Нужна реальная ликвидность (AIX > 0 и TOKEN > 0)"

        record = TokenRecord(
            symbol=symbol, name=name, creator=creator,
            total_supply=total_supply, decimals=18,
            emoji=emoji, created_at=time.time(),
            description=description,
            initial_pool_aix=initial_pool_aix,
            initial_pool_token=initial_pool_token,
            usd_price=usd_price,
        )
        self.tokens[symbol] = record
        self._save()
        return True, f"Токен {symbol} зарегистрирован"

    def get(self, symbol: str) -> Optional[TokenRecord]:
        return self.tokens.get(symbol.upper())

    def list_all(self) -> list[TokenRecord]:
        return list(self.tokens.values())

    def list_custom(self) -> list[TokenRecord]:
        return [t for sym, t in self.tokens.items() if sym not in BASE_TOKENS]

    def exists(self, symbol: str) -> bool:
        return symbol.upper() in self.tokens
