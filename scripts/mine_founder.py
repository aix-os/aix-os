"""
AIX OS — майнинг 1 000 000 AIX на кошелёк founder.

Майнит блоки последовательно, пока баланс founder не достигнет
цели. Показывает прогресс каждые 50 блоков. Работает через ноду A.

При 50 AIX за блок, для 1 000 000 AIX нужно 20 000 блоков.
На CPU это ~3-4 часа. Можно прервать и продолжить — прогресс сохраняется.

Запуск:
    .venv\\Scripts\\python.exe scripts\\mine_founder.py

Дополнительно:
    --target 1000000     сколько AIX намайнить (по умолчанию 1 000 000)
    --node-url http://127.0.0.1:8010
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.wallet import Wallet  # noqa: E402


DEFAULT_NODE_URL = "http://127.0.0.1:8010"


def node_get(base_url: str, path: str):
    try:
        r = requests.get(f"{base_url}{path}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def node_post(base_url: str, path: str, body: dict):
    r = requests.post(f"{base_url}{path}", json=body, timeout=120)
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(f"POST {path}: {detail}")
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=float, default=1_000_000.0,
                        help="Сколько AIX намайнить (по умолчанию 1 000 000)")
    parser.add_argument("--node-url", default=DEFAULT_NODE_URL)
    parser.add_argument("--wallet", default="founder")
    args = parser.parse_args()

    node_url = args.node_url.rstrip("/")

    if not Wallet.exists(args.wallet):
        print(f"[FATAL] Кошелёк '{args.wallet}' не найден.")
        print("   Сначала: .venv\\Scripts\\python.exe scripts\\setup_founder_wallets.py")
        return 1
    w = Wallet.load(args.wallet)

    print(f"AIX OS — майнинг на {args.wallet}")
    print(f"  Нода:  {node_url}")
    print(f"  Адрес: {w.address}")
    print(f"  Цель:  {args.target:,.0f} AIX")
    print()

    status = node_get(node_url, "/status")
    if not status:
        print(f"[FATAL] Нода не отвечает.")
        print("   Запусти: .\\scripts\\run_all.ps1")
        return 1

    print(f"Текущая высота: {status.get('height')}")
    start_balance = 0.0
    bal = node_get(node_url, f"/balance/{w.address}")
    if bal:
        start_balance = bal.get("balance_aix", 0)
        print(f"Текущий баланс: {start_balance:,.2f} AIX")
    print()

    blocks_mined = 0
    t_start = time.time()
    try:
        while True:
            bal = node_get(node_url, f"/balance/{w.address}")
            current = bal.get("balance_aix", 0) if bal else 0
            if current >= args.target:
                print()
                print(f"✅ Готово! Баланс: {current:,.2f} AIX")
                break

            try:
                res = node_post(node_url, "/mine", {
                    "miner_address": w.address,
                    "broadcast": True,
                })
            except RuntimeError as e:
                print(f"  майнинг упал: {e}")
                print("  жду 5 сек...")
                time.sleep(5)
                continue

            blocks_mined += 1
            block_idx = res.get("block_index", "?")
            time_sec = res.get("time_seconds", 0)
            reward = res.get("reward_aix", 50)

            if blocks_mined % 50 == 0 or blocks_mined <= 5:
                elapsed = time.time() - t_start
                speed = blocks_mined / elapsed if elapsed > 0 else 0
                remaining = max(0, args.target - current)
                eta_sec = int(remaining / (speed * reward)) if speed > 0 else 0
                eta_min = eta_sec // 60
                print(f"  блок #{block_idx:>6}  "
                      f"({time_sec:>6.2f}с)  "
                      f"баланс: {current:>12,.2f} / {args.target:,.0f}  "
                      f"({blocks_mined} блоков, ETA ~{eta_min} мин)")
    except KeyboardInterrupt:
        print()
        print("Прервано пользователем. Прогресс сохранён.")

    elapsed = time.time() - t_start
    print()
    print(f"Итого: замайнено блоков: {blocks_mined}")
    print(f"       потрачено: {elapsed/60:.1f} мин")
    bal = node_get(node_url, f"/balance/{w.address}")
    if bal:
        print(f"       баланс: {bal.get('balance_aix', 0):,.2f} AIX")
    return 0


if __name__ == "__main__":
    sys.exit(main())