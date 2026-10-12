"""
AIX OS — Внутренний AMM-свап (DeFi-симуляция).

Обменник типа Uniswap V2 внутри AIX OS.

Как работает:
1. Любой создаёт пул: вносит оба токена → получает LP-токены
2. Формула x * y = k (constant product) определяет курс
3. Обмен идёт по кривой, никто не может подкрутить
4. Комиссия 0.3% остаётся в пуле → LP-держатели зарабатывают

ЗАЩИТА ОТ ОПУСТОШЕНИЯ:
- Резерв не может опуститься ниже 5% от исходного
- Аналог MINIMUM_LIQUIDITY в Uniswap V2
- Пул никогда не станет 0 × 0 = 0

⚠️ AIX в свапе — это AIX-SIM (виртуальная версия).
   Реальный AIX из блокчейна появится с мостом к Ethereum/BSC.

Хранение: data/swap_{port}.json
"""

import json
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# Доступные токены для свапа
SIM_TOKENS = {
    "AIX-SIM":   {"name": "AIX (сим)", "emoji": "🤖", "decimals": 18},
    "USDT-SIM":  {"name": "USDT (сим)", "emoji": "💵", "decimals": 18},
    "BTC-SIM":   {"name": "BTC (сим)", "emoji": "🟠", "decimals": 18},
    "ETH-SIM":   {"name": "ETH (сим)", "emoji": "💎", "decimals": 18},
    "SOL-SIM":   {"name": "SOL (сим)", "emoji": "🟣", "decimals": 18},
}

# Комиссия свапа (в процентах), идёт в пул → LP-держателям
DEFAULT_FEE_PERCENT = 0.3

# Минимум ликвидности на пул (10 токенов в атомарных единицах)
MIN_LIQUIDITY = 10 * 10 ** 18

# Защита от опустошения: резерв не может упасть ниже этого % от исходного
MIN_RESERVE_PERCENT = 5

# Faucet: сколько выдаёт за раз
FAUCET_AMOUNT = 1000 * 10 ** 18

# Faucet cooldown (для теста — 0, в продакшене — 24 часа)
FAUCET_COOLDOWN_SECONDS = 0


# =============================================================================
# ФОРМУЛА AMM
# =============================================================================

def compute_swap_output(reserve_in: int, reserve_out: int,
                        amount_in: int, fee_percent: float) -> int:
    """
    Формула Uniswap V2:
      k = reserve_in * reserve_out
      amount_in_with_fee = amount_in * (1 - fee)
      new_reserve_in = reserve_in + amount_in_with_fee
      new_reserve_out = k / new_reserve_in
      amount_out = reserve_out - new_reserve_out
    """
    if amount_in <= 0:
        return 0
    if reserve_in <= 0 or reserve_out <= 0:
        return 0

    amount_in_with_fee = amount_in * (1000 - int(fee_percent * 10)) // 1000
    k = reserve_in * reserve_out
    new_reserve_in = reserve_in + amount_in_with_fee
    new_reserve_out = k // new_reserve_in
    amount_out = reserve_out - new_reserve_out
    return max(0, amount_out)


def compute_lp_tokens(amount_a: int, amount_b: int,
                      reserve_a: int, reserve_b: int,
                      total_lp: int) -> int:
    """
    Сколько LP-токенов выдадут за добавление ликвидности.
    Первое внесение: LP = sqrt(amount_a * amount_b)
    Последующие: LP = min(amount_a * total_lp / reserve_a,
                          amount_b * total_lp / reserve_b)
    """
    if total_lp == 0:
        return int((amount_a * amount_b) ** 0.5)
    lp_from_a = amount_a * total_lp // reserve_a
    lp_from_b = amount_b * total_lp // reserve_b
    return min(lp_from_a, lp_from_b)


# =============================================================================
# ПУЛ
# =============================================================================

@dataclass
class SwapPool:
    """Пул ликвидности для пары токенов."""
    id: str                       # "AIX-SIM/USDT-SIM" (алфавитный порядок)
    token_a: str                  # всегда алфавитно первый
    token_b: str
    reserve_a: int                # в атомарных единицах
    reserve_b: int
    total_lp: int                 # всего LP-токенов
    lp_holders: dict = field(default_factory=dict)  # {address: lp_amount}
    fee_percent: float = DEFAULT_FEE_PERCENT
    created_at: float = 0.0
    created_by: str = ""
    # Исходная ликвидность (для защиты от опустошения)
    initial_reserve_a: int = 0
    initial_reserve_b: int = 0

    def price_a_in_b(self) -> float:
        if self.reserve_a == 0:
            return 0.0
        return self.reserve_b / self.reserve_a

    def price_b_in_a(self) -> float:
        if self.reserve_b == 0:
            return 0.0
        return self.reserve_a / self.reserve_b

    def min_allowed_reserve_a(self) -> int:
        """Минимум резерва A, ниже которого пул опуститься не может."""
        base = self.initial_reserve_a if self.initial_reserve_a > 0 else self.reserve_a
        return base * MIN_RESERVE_PERCENT // 100

    def min_allowed_reserve_b(self) -> int:
        """Минимум резерва B."""
        base = self.initial_reserve_b if self.initial_reserve_b > 0 else self.reserve_b
        return base * MIN_RESERVE_PERCENT // 100

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SwapPool":
        # Обратная совместимость: если нет initial_reserve_*
        if "initial_reserve_a" not in data:
            data["initial_reserve_a"] = data.get("reserve_a", 0)
        if "initial_reserve_b" not in data:
            data["initial_reserve_b"] = data.get("reserve_b", 0)
        return cls(**data)

    def __repr__(self):
        return (f"SwapPool({self.id}, "
                f"A={self.reserve_a / 10**18:.2f}, "
                f"B={self.reserve_b / 10**18:.2f})")


def make_pool_id(token_x: str, token_y: str) -> tuple:
    """Возвращает (pool_id, token_a, token_b) где token_a <= token_b."""
    a, b = sorted([token_x, token_y])
    return f"{a}/{b}", a, b


# =============================================================================
# МЕНЕДЖЕР
# =============================================================================

class SwapManager:
    """Менеджер пулов и балансов SIM-токенов."""

    def __init__(self, storage_path, blockchain=None):
        self.storage_path = Path(storage_path)
        self.pools: dict = {}
        self.balances: dict = {}
        self.faucet_last: dict = {}
        self.blockchain = blockchain
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("pools", []):
                p = SwapPool.from_dict(item)
                self.pools[p.id] = p
            self.balances = data.get("balances", {})
            self.faucet_last = data.get("faucet_last", {})
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: не удалось загрузить свапы: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "pools": [p.to_dict() for p in self.pools.values()],
                "balances": self.balances,
                "faucet_last": self.faucet_last,
            }, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    # =========================================================================
    # БАЛАНСЫ
    # =========================================================================

    def get_balance(self, address: str, token: str) -> int:
        return self.balances.get(address, {}).get(token, 0)

    def add_balance(self, address: str, token: str, amount: int):
        if address not in self.balances:
            self.balances[address] = {}
        self.balances[address][token] = self.balances[address].get(token, 0) + amount

    def sub_balance(self, address: str, token: str, amount: int) -> bool:
        if self.get_balance(address, token) < amount:
            return False
        self.balances[address][token] -= amount
        return True

    def all_balances(self, address: str) -> dict:
        return dict(self.balances.get(address, {}))

    # =========================================================================
    # FAUCET
    # =========================================================================

    def faucet(self, address: str, token: str) -> tuple:
        if token not in SIM_TOKENS:
            return False, f"Неизвестный токен: {token}", 0
        last = self.faucet_last.get(address, 0)
        now = time.time()
        wait = FAUCET_COOLDOWN_SECONDS - (now - last)
        if wait > 0:
            return False, f"Cooldown: подожди {int(wait)} сек", 0
        self.add_balance(address, token, FAUCET_AMOUNT)
        self.faucet_last[address] = now
        self._save()
        return True, "OK", FAUCET_AMOUNT

    # =========================================================================
    # ПУЛЫ
    # =========================================================================

    def get_pool(self, pool_id: str) -> Optional[SwapPool]:
        parts = pool_id.upper().split("/")
        if len(parts) != 2:
            return None
        normalized = []
        for p in parts:
            p = p.strip()
            if not p.endswith("-SIM"):
                p = f"{p}-SIM" if p in ("AIX", "USDT", "BTC", "ETH", "SOL") else p
            normalized.append(p)
        pid, _, _ = make_pool_id(normalized[0], normalized[1])
        return self.pools.get(pid)

    def list_pools(self) -> list:
        return sorted(self.pools.values(), key=lambda p: p.created_at)

    def create_pool(self, token_x: str, token_y: str,
                    amount_x: int, amount_y: int,
                    creator: str) -> tuple:
        if token_x == token_y:
            return False, "Нельзя создать пул одинаковых токенов", None
        if token_x not in SIM_TOKENS or token_y not in SIM_TOKENS:
            return False, f"Неизвестный токен. Доступные: {', '.join(SIM_TOKENS.keys())}", None
        if amount_x <= 0 or amount_y <= 0:
            return False, "Суммы должны быть положительными", None

        pool_id, token_a, token_b = make_pool_id(token_x, token_y)

        if pool_id in self.pools:
            return False, f"Пул {pool_id} уже существует", None

        if token_a == token_x:
            amount_a, amount_b = amount_x, amount_y
        else:
            amount_a, amount_b = amount_y, amount_x

        if amount_a * amount_b < MIN_LIQUIDITY * MIN_LIQUIDITY:
            return False, "Слишком маленькая начальная ликвидность", None

        if not self.sub_balance(creator, token_a, amount_a):
            return False, f"Недостаточно {token_a}", None
        if not self.sub_balance(creator, token_b, amount_b):
            self.add_balance(creator, token_a, amount_a)
            return False, f"Недостаточно {token_b}", None

        lp_tokens = compute_lp_tokens(amount_a, amount_b, 0, 0, 0)
        pool = SwapPool(
            id=pool_id,
            token_a=token_a,
            token_b=token_b,
            reserve_a=amount_a,
            reserve_b=amount_b,
            total_lp=lp_tokens,
            lp_holders={creator: lp_tokens},
            created_at=time.time(),
            created_by=creator,
            initial_reserve_a=amount_a,
            initial_reserve_b=amount_b,
        )
        self.pools[pool_id] = pool
        self._save()
        return True, f"OK. LP-токенов выдано: {lp_tokens / 10**18:.4f}", pool

    # =========================================================================
    # ЛИКВИДНОСТЬ
    # =========================================================================

    def add_liquidity(self, pool_id: str, address: str,
                      amount_a: int, amount_b: int) -> tuple:
        pool = self.get_pool(pool_id)
        if pool is None:
            return False, "Пул не найден", 0

        if amount_a <= 0 or amount_b <= 0:
            return False, "Суммы должны быть положительными", 0

        expected_b = amount_a * pool.reserve_b // pool.reserve_a
        if abs(amount_b - expected_b) > expected_b * 0.02:
            return False, (f"Пропорция должна быть ~ {pool.reserve_b/pool.reserve_a:.6f}. "
                          f"Для {amount_a/10**18:.4f} {pool.token_a} нужно "
                          f"~{expected_b/10**18:.4f} {pool.token_b}"), 0

        if not self.sub_balance(address, pool.token_a, amount_a):
            return False, f"Недостаточно {pool.token_a}", 0
        if not self.sub_balance(address, pool.token_b, amount_b):
            self.add_balance(address, pool.token_a, amount_a)
            return False, f"Недостаточно {pool.token_b}", 0

        lp_tokens = compute_lp_tokens(amount_a, amount_b,
                                      pool.reserve_a, pool.reserve_b,
                                      pool.total_lp)
        if lp_tokens <= 0:
            self.add_balance(address, pool.token_a, amount_a)
            self.add_balance(address, pool.token_b, amount_b)
            return False, "Слишком маленькое добавление", 0

        pool.reserve_a += amount_a
        pool.reserve_b += amount_b
        pool.total_lp += lp_tokens
        pool.lp_holders[address] = pool.lp_holders.get(address, 0) + lp_tokens
        # Обновляем исходные резервы (растут)
        pool.initial_reserve_a += amount_a
        pool.initial_reserve_b += amount_b
        self._save()

        return True, "OK", lp_tokens

    def remove_liquidity(self, pool_id: str, address: str,
                         lp_amount: int) -> tuple:
        pool = self.get_pool(pool_id)
        if pool is None:
            return False, "Пул не найден", 0, 0

        held = pool.lp_holders.get(address, 0)
        if held < lp_amount:
            return False, (f"У вас только {held/10**18:.4f} LP, "
                          f"запрошено {lp_amount/10**18:.4f}"), 0, 0

        share_a = pool.reserve_a * lp_amount // pool.total_lp
        share_b = pool.reserve_b * lp_amount // pool.total_lp

        pool.reserve_a -= share_a
        pool.reserve_b -= share_b
        pool.total_lp -= lp_amount
        pool.lp_holders[address] = held - lp_amount
        if pool.lp_holders[address] == 0:
            del pool.lp_holders[address]

        # Пропорционально уменьшаем initial_reserve
        share_ratio = lp_amount * 10**18 // pool.total_lp if pool.total_lp > 0 else 0
        # Защита от потери точности
        if pool.total_lp + lp_amount > 0:
            ratio = lp_amount / (pool.total_lp + lp_amount)
            pool.initial_reserve_a = int(pool.initial_reserve_a * (1 - ratio))
            pool.initial_reserve_b = int(pool.initial_reserve_b * (1 - ratio))

        self.add_balance(address, pool.token_a, share_a)
        self.add_balance(address, pool.token_b, share_b)
        self._save()

        return True, "OK", share_a, share_b

    # =========================================================================
    # СВАП
    # =========================================================================

    def get_quote(self, pool_id: str, from_token: str,
                  amount_in: int) -> tuple:
        pool = self.get_pool(pool_id)
        if pool is None:
            return False, "Пул не найден", {}

        if from_token not in (pool.token_a, pool.token_b):
            return False, f"Токен {from_token} не в пуле {pool.id}", {}

        if amount_in <= 0:
            return False, "Сумма должна быть положительной", {}

        if from_token == pool.token_a:
            reserve_in = pool.reserve_a
            reserve_out = pool.reserve_b
            to_token = pool.token_b
            min_out_reserve = pool.min_allowed_reserve_b()
        else:
            reserve_in = pool.reserve_b
            reserve_out = pool.reserve_a
            to_token = pool.token_a
            min_out_reserve = pool.min_allowed_reserve_a()

        amount_out = compute_swap_output(reserve_in, reserve_out,
                                         amount_in, pool.fee_percent)
        if amount_out <= 0:
            return False, "Слишком маленькая сумма для обмена", {}

        # ЗАЩИТА: не даём показывать курс, если сделка опустошит пул
        if reserve_out - amount_out < min_out_reserve:
            return False, (f"Сделка слишком велика для пула (защита от опустошения). "
                          f"Максимум можно вывести: "
                          f"{(reserve_out - min_out_reserve) / 10**18:.4f} {to_token}"), {}

        price_before = (reserve_out / reserve_in if reserve_in > 0 else 0)
        price_after = amount_out / amount_in if amount_in > 0 else 0
        slippage = ((price_before - price_after) / price_before * 100
                   if price_before > 0 else 0)

        return True, "OK", {
            "pool_id": pool.id,
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": amount_in,
            "amount_in_aix": amount_in / 10**18,
            "amount_out": amount_out,
            "amount_out_aix": amount_out / 10**18,
            "price": price_before,
            "execution_price": price_after,
            "slippage_percent": slippage,
            "fee_percent": pool.fee_percent,
        }

    def swap(self, pool_id: str, address: str,
             from_token: str, amount_in: int) -> tuple:
        pool = self.get_pool(pool_id)
        if pool is None:
            return False, "Пул не найден", {}

        if amount_in <= 0:
            return False, "Сумма должна быть положительной", {}

        if from_token not in (pool.token_a, pool.token_b):
            return False, f"Токен {from_token} не в пуле {pool.id}", {}

        balance = self.get_balance(address, from_token)
        if balance < amount_in:
            return False, (f"Недостаточно {from_token}. "
                          f"У вас: {balance/10**18:.4f}, "
                          f"нужно: {amount_in/10**18:.4f}"), {}

        if from_token == pool.token_a:
            reserve_in = pool.reserve_a
            reserve_out = pool.reserve_b
            to_token = pool.token_b
            min_out_reserve = pool.min_allowed_reserve_b()
        else:
            reserve_in = pool.reserve_b
            reserve_out = pool.reserve_a
            to_token = pool.token_a
            min_out_reserve = pool.min_allowed_reserve_a()

        amount_out = compute_swap_output(reserve_in, reserve_out,
                                         amount_in, pool.fee_percent)
        if amount_out <= 0:
            return False, "Слишком маленькая сумма для обмена", {}

        # ЗАЩИТА: не даём опустошить пул
        if reserve_out - amount_out < min_out_reserve:
            return False, (f"Сделка слишком велика для пула (защита от опустошения). "
                          f"Максимум можно вывести: "
                          f"{(reserve_out - min_out_reserve) / 10**18:.4f} {to_token}"), {}

        if not self.sub_balance(address, from_token, amount_in):
            return False, "Ошибка списания", {}

        self.add_balance(address, to_token, amount_out)

        if from_token == pool.token_a:
            pool.reserve_a += amount_in
            pool.reserve_b -= amount_out
        else:
            pool.reserve_b += amount_in
            pool.reserve_a -= amount_out

        self._save()

        price_before = (reserve_out / reserve_in if reserve_in > 0 else 0)
        price_after = amount_out / amount_in if amount_in > 0 else 0

        return True, "OK", {
            "pool_id": pool.id,
            "from_token": from_token,
            "to_token": to_token,
            "amount_in": amount_in,
            "amount_in_aix": amount_in / 10**18,
            "amount_out": amount_out,
            "amount_out_aix": amount_out / 10**18,
            "price_before": price_before,
            "price_after": price_after,
            "slippage_percent": ((price_before - price_after) / price_before * 100
                                if price_before > 0 else 0),
            "fee_percent": pool.fee_percent,
        }

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def stats(self) -> dict:
        pools_info = []
        for pool in self.pools.values():
            pools_info.append({
                "id": pool.id,
                "token_a": pool.token_a,
                "token_b": pool.token_b,
                "reserve_a_aix": pool.reserve_a / 10**18,
                "reserve_b_aix": pool.reserve_b / 10**18,
                "initial_reserve_a_aix": pool.initial_reserve_a / 10**18,
                "initial_reserve_b_aix": pool.initial_reserve_b / 10**18,
                "min_allowed_a_aix": pool.min_allowed_reserve_a() / 10**18,
                "min_allowed_b_aix": pool.min_allowed_reserve_b() / 10**18,
                "price_a_in_b": pool.price_a_in_b(),
                "price_b_in_a": pool.price_b_in_a(),
                "total_lp": pool.total_lp / 10**18,
                "lp_holders": len(pool.lp_holders),
                "fee_percent": pool.fee_percent,
                "created_at": pool.created_at,
            })

        return {
            "total_pools": len(self.pools),
            "total_holders": len(self.balances),
            "pools": pools_info,
        }

    def pool_lp_info(self, pool_id: str, address: str) -> dict:
        pool = self.get_pool(pool_id)
        if pool is None:
            return {}
        held = pool.lp_holders.get(address, 0)
        share = held / pool.total_lp if pool.total_lp > 0 else 0
        share_a = pool.reserve_a * held // pool.total_lp if pool.total_lp > 0 else 0
        share_b = pool.reserve_b * held // pool.total_lp if pool.total_lp > 0 else 0
        return {
            "pool_id": pool.id,
            "lp_tokens": held,
            "lp_tokens_aix": held / 10**18,
            "share_percent": share * 100,
            "share_a": share_a,
            "share_a_aix": share_a / 10**18,
            "share_b": share_b,
            "share_b_aix": share_b / 10**18,
        }

    # =========================================================================
    # СИНХРОНИЗАЦИЯ
    # =========================================================================

    def export_all(self) -> dict:
        return {
            "pools": [p.to_dict() for p in self.pools.values()],
            "balances": self.balances,
        }

    def import_state(self, data: dict) -> tuple:
        added_pools = 0
        added_balances = 0

        for pool_data in data.get("pools", []):
            try:
                new_p = SwapPool.from_dict(pool_data)
                existing = self.pools.get(new_p.id)
                if existing is None:
                    self.pools[new_p.id] = new_p
                    added_pools += 1
                else:
                    if (new_p.reserve_a + new_p.reserve_b) > (existing.reserve_a + existing.reserve_b):
                        self.pools[new_p.id] = new_p
            except Exception as e:
                print(f"WARN: import pool: {e}")

        remote_balances = data.get("balances", {})
        for addr, tokens in remote_balances.items():
            if addr not in self.balances:
                self.balances[addr] = dict(tokens)
                added_balances += 1
            else:
                for tok, bal in tokens.items():
                    local = self.balances[addr].get(tok, 0)
                    if bal > local:
                        self.balances[addr][tok] = bal

        if added_pools > 0 or added_balances > 0:
            self._save()

        return True, f"+{added_pools} pools, +{added_balances} addresses"

    def __len__(self):
        return len(self.pools)

    def __repr__(self):
        return f"SwapManager({len(self.pools)} pools)"


# =============================================================================
# ТЕСТ
# =============================================================================

if __name__ == "__main__":
    print("💱 Тестирую AMM-свап с защитой от опустошения...\n")

    import tempfile
    tmp = Path(tempfile.gettempdir()) / "test_swap.json"
    if tmp.exists():
        tmp.unlink()

    mgr = SwapManager(tmp)

    alice = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
    bob = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"

    print("1. Faucet:")
    for token in ["AIX-SIM", "USDT-SIM", "BTC-SIM"]:
        mgr.add_balance(alice, token, 100000 * 10**18)
        print(f"   {token}: выдано 100000")
    mgr.add_balance(bob, "USDT-SIM", 100000 * 10**18)
    print(f"   USDT-SIM для Bob: выдано 100000")
    print()

    print("2. Создание пула AIX-SIM/USDT-SIM (1000/500):")
    ok, msg, pool = mgr.create_pool("AIX-SIM", "USDT-SIM",
                                    1000 * 10**18, 500 * 10**18, alice)
    print(f"   {ok} — {msg}")
    if pool:
        print(f"   Курс: 1 {pool.token_a} = {pool.price_a_in_b():.6f} {pool.token_b}")
        print(f"   Минимум A (5%): {pool.min_allowed_reserve_a()/10**18:.2f} AIX")
        print(f"   Минимум B (5%): {pool.min_allowed_reserve_b()/10**18:.2f} USDT")
    print()

    print("3. ЗАЩИТА: пытаемся продать 999 AIX (опустошит пул):")
    ok, msg, q = mgr.get_quote("AIX/USDT", "AIX-SIM", 999 * 10**18)
    print(f"   {ok} — {msg}")
    print()

    print("4. Нормальная сделка: 100 AIX:")
    ok, msg, q = mgr.get_quote("AIX/USDT", "AIX-SIM", 100 * 10**18)
    if ok:
        print(f"   Получите: {q['amount_out_aix']:.4f} USDT-SIM")
        print(f"   Slippage: {q['slippage_percent']:.4f}%")
    print()

    print("5. Пытаемся продать 80% резерва (тоже защита):")
    ok, msg, q = mgr.get_quote("AIX/USDT", "AIX-SIM", 800 * 10**18)
    print(f"   {ok} — {msg}")
    print()

    print("6. Обратная сделка Bob: 100 USDT → AIX:")
    ok, msg, s = mgr.swap("AIX/USDT", bob, "USDT-SIM", 100 * 10**18)
    if ok:
        print(f"   Bob получил: {s['amount_out_aix']:.4f} AIX-SIM")
    print()

    print("7. Пул после сделки:")
    ok, msg, info = mgr.get_quote("AIX/USDT", "AIX-SIM", 1 * 10**18)  # для обновления
    print(f"   Резервы: {pool.reserve_a/10**18:.4f} AIX + {pool.reserve_b/10**18:.4f} USDT")

    tmp.unlink()
    print("\n✅ AMM-свап с защитой работает.")