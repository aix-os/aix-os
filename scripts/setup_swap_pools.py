"""
AIX OS — создание стартовых пулов ликвидности.

ЭКОНОМИКА (декабрь 2026):
  1 AIX = $100

В каждый пул кладём 1000 AIX (= $100 000) +
эквивалент $100 000 во втором токене.

Запуск:
    .venv\\Scripts\\python.exe scripts\\setup_swap_pools.py

Требует подтверждения y/N.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.protocols.swap import SwapManager  # noqa: E402
from core.wallet import Wallet  # noqa: E402
import config  # noqa: E402


# Курс AIX и токенов в USD
AIX_PRICE_USD = 100.0

TOKEN_PRICES_USD = {
    "USDT":  1.0,
    "USDC":  1.0,
    "BTC":   50000.0,
    "ETH":   3000.0,
    "BNB":   500.0,
    "SOL":   150.0,
    "TON":   5.0,
    "XRP":   0.5,
    "ADA":   0.4,
    "DOGE":  0.1,
    "DOT":   5.0,
    "MATIC": 0.5,
    "AVAX":  30.0,
    "LTC":   100.0,
    "TRX":   0.15,
    "LINK":  15.0,
    "ATOM":  7.0,
    "UNI":   10.0,
    "XMR":   150.0,
}

AIX_PER_POOL = 1000.0
USD_PER_POOL = AIX_PER_POOL * AIX_PRICE_USD  # = 100 000

SATO = config.SATOSHI


def build_pools():
    pools = []
    for token, price_usd in TOKEN_PRICES_USD.items():
        amount_y = USD_PER_POOL / price_usd
        pools.append(("AIX", token, AIX_PER_POOL, amount_y))
    return pools


POOLS = build_pools()


def stop_nodes() -> None:
    """Остановить только процессы ноды (network\\server.py), не трогая
    текущий скрипт."""
    print("Останавливаю ноды...")
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'network[\\\\/]server' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            check=False,
            timeout=15,
        )
        time.sleep(1.5)
        print("  ноды остановлены (если были запущены)")
    except Exception as e:
        print(f"  предупреждение: {e}")


def start_nodes() -> None:
    """Запустить ноды через run_all.ps1 в отдельном окне."""
    print("Запускаю ноды...")
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Start-Process",
                "powershell",
                "-ArgumentList",
                f"'-NoExit','-NoProfile','-Command','cd ''{ROOT}''; "
                f".\\scripts\\run_all.ps1''",
            ],
            cwd=str(ROOT),
        )
        print("  ноды запускаются в отдельном окне")
    except Exception as e:
        print(f"  предупреждение: {e}")
        print("  запусти вручную: .\\scripts\\run_all.ps1")


def clear_swap_files() -> None:
    print("Чищу swap-файлы...")
    data_dir = config.DATA_DIR
    patterns = (
        "swap_8010.json", "swap_8011.json",
        "swap_8010.json.bak", "swap_8011.json.bak",
        "swap_8010.json.tmp", "swap_8011.json.tmp",
    )
    for pattern in patterns:
        p = data_dir / pattern
        if p.exists():
            p.unlink()
            print(f"  удалён {p.name}")


def setup_for_port(port: int, creator_addr: str) -> None:
    print(f"\nПорт {port}:")
    path = config.DATA_DIR / f"swap_{port}.json"
    mgr = SwapManager(path)

    supply_aix = 1_000_000 * SATO
    mgr.add_balance(creator_addr, "AIX", supply_aix)
    print(f"  выдано Alice {supply_aix / SATO:,.0f} AIX")

    for token, price_usd in TOKEN_PRICES_USD.items():
        amount = 2 * USD_PER_POOL / price_usd
        mgr.add_balance(creator_addr, token, int(amount * SATO))
    print("  выданы эквиваленты $100 000 × 2 для каждого токена")

    created = 0
    for token_x, token_y, amt_x, amt_y in POOLS:
        amount_x = int(amt_x * SATO)
        amount_y = int(amt_y * SATO)
        ok, msg, pool = mgr.create_pool(token_x, token_y,
                                        amount_x, amount_y,
                                        creator_addr)
        if ok:
            created += 1
            if pool.token_a == "AIX":
                price = pool.price_a_in_b()
                print(f"  OK  {pool.id:20s}  1 AIX = {price:>15,.6f} {pool.token_b}")
            else:
                price = pool.price_b_in_a()
                print(f"  OK  {pool.id:20s}  1 AIX = {price:>15,.6f} {pool.token_a}")
        else:
            print(f"  FAIL {token_x}/{token_y}: {msg}")

    mgr._save()
    print(f"  создано пулов: {created}")


def main() -> int:
    print("=" * 60)
    print("  AIX OS — пересоздание пулов ликвидности")
    print("=" * 60)
    print()
    print(f"ЭКОНОМИКА: 1 AIX = ${AIX_PRICE_USD:.0f}")
    print(f"Пулов будет: {len(POOLS)}")
    print(f"В каждом пуле: {AIX_PER_POOL:.0f} AIX (${USD_PER_POOL:,.0f}) "
          f"+ эквивалент ${USD_PER_POOL:,.0f}")
    print()
    print("Что произойдёт:")
    print("  1. Остановка нод (только процессов server.py)")
    print("  2. Удаление старых swap_*.json")
    print("  3. Создание новых пулов для A и B")
    print("  4. Запуск нод в отдельном окне")
    print()

    ans = input("Продолжить? [y/N] ").strip().lower()
    if ans not in ("y", "yes", "д", "да"):
        print("Отменено.")
        return 0

    if not Wallet.exists("alice"):
        print("[FATAL] Кошелёк 'alice' не найден")
        return 1
    alice = Wallet.load("alice")
    print(f"\nСоздатель пулов: alice ({alice.address})")

    stop_nodes()
    clear_swap_files()
    setup_for_port(8010, alice.address)
    setup_for_port(8011, alice.address)
    start_nodes()

    print()
    print("=" * 60)
    print("  Готово. 1 AIX = $100")
    print("=" * 60)
    print()
    print("Через 5-10 секунд проверь:")
    print("  Invoke-RestMethod http://127.0.0.1:8010/swap/pools | Select count")
    print("  или открой http://localhost:9000 вкладку 💱 Обмен")
    return 0


if __name__ == "__main__":
    sys.exit(main())