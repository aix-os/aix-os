"""
AIX OS -- Faucet setup.

Настраивает кран на чистой цепочке:
1. Проверяет, что нода A запущена
2. Майнит N блоков на кошелёк 'miner' (первый майнер)
3. Отправляет накопленные AIX с 'miner' на кошелёк-казначей
4. Назначает кошелёк-казначей в FaucetManager

По умолчанию: майнер = 'miner', казначей = 'alice', блоков = 20.

Запуск:
    .venv\\Scripts\\python.exe scripts\\faucet_setup.py
    .venv\\Scripts\\python.exe scripts\\faucet_setup.py --miner miner --treasury alice --blocks 20

После этого ноды нужно перезапустить, чтобы казначей подхватился в API.
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
from core.protocols.faucet import FaucetManager  # noqa: E402
import config  # noqa: E402


DEFAULT_NODE_URL = "http://127.0.0.1:8010"


def node_get(base_url: str, path: str) -> dict | None:
    try:
        r = requests.get(f"{base_url}{path}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def node_post(base_url: str, path: str, body: dict) -> dict:
    r = requests.post(f"{base_url}{path}", json=body, timeout=60)
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(f"POST {path} -> {r.status_code}: {detail}")
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="AIX Faucet setup")
    parser.add_argument("--miner", default="miner", help="Кошелёк-майнер")
    parser.add_argument("--treasury", default="alice", help="Кошелёк-казначей")
    parser.add_argument("--blocks", type=int, default=20,
                        help="Сколько блоков замайнить")
    parser.add_argument("--node-url", default=DEFAULT_NODE_URL,
                        help="URL ноды (по умолчанию http://127.0.0.1:8010)")
    args = parser.parse_args()

    node_url = args.node_url.rstrip("/")

    print(f"AIX Faucet setup")
    print(f"  Нода:     {node_url}")
    print(f"  Майнер:   {args.miner}")
    print(f"  Казначей: {args.treasury}")
    print(f"  Блоков:   {args.blocks}")
    print()

    # --- 1. Нода жива? ---
    status = node_get(node_url, "/status")
    if not status:
        print(f"[FATAL] Нода {node_url} не отвечает.")
        print("   Запусти ноды:  .\\scripts\\run_all.ps1")
        return 1

    height = status.get("height", 0)
    print(f"Текущая высота: {height}")
    if height > 10:
        print(f"[WARN] Высота {height} > 10. Похоже, это не чистая цепочка.")
        ans = input("Продолжить? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return 0

    # --- 2. Кошельки ---
    if not Wallet.exists(args.miner):
        print(f"[FATAL] Кошелёк '{args.miner}' не найден.")
        return 1
    if not Wallet.exists(args.treasury):
        print(f"[FATAL] Кошелёк '{args.treasury}' не найден.")
        return 1

    miner_w = Wallet.load(args.miner)
    treasury_w = Wallet.load(args.treasury)
    print(f"Майнер:   {args.miner} ({miner_w.address})")
    print(f"Казначей: {args.treasury} ({treasury_w.address})")

    # --- 3. Майнинг ---
    print()
    print(f"Майним {args.blocks} блоков на '{args.miner}'...")
    for i in range(args.blocks):
        try:
            res = node_post(node_url, "/mine", {
                "miner_address": miner_w.address,
                "broadcast": True,
            })
        except RuntimeError as e:
            print(f"[FATAL] Майнинг упал: {e}")
            return 1
        print(f"  [{i + 1}/{args.blocks}] блок #{res['block_index']} "
              f"({res['time_seconds']}с, +{res['reward_aix']} AIX)")

    # --- 4. Проверяем баланс майнера ---
    bal = node_get(node_url, f"/balance/{miner_w.address}")
    if not bal:
        print("[FATAL] Не могу получить баланс майнера")
        return 1
    miner_balance = bal.get("available_aix", 0)
    print()
    print(f"Баланс майнера: {miner_balance} AIX")

    # Оставим майнеру небольшой запас на комиссии, остальное отправим казначею
    send_amount = miner_balance - 5.0
    if send_amount <= 0:
        print(f"[WARN] Мало намайнено ({miner_balance} AIX). "
              f"Увеличь --blocks.")
        return 1

    print(f"Отправляем {send_amount} AIX майнеру -> казначею...")

    # --- 5. Отправка ---
    try:
        res = node_post(node_url, "/send", {
            "sender": miner_w.address,
            "recipient": treasury_w.address,
            "amount": 0,
            "amount_aix": send_amount,
            "private_key": miner_w.private_key,
            "message": "Faucet treasury fund",
        })
        print(f"  TX: {res.get('tx_id', '?')[:32]}...")
    except RuntimeError as e:
        print(f"[FATAL] Отправка упала: {e}")
        return 1

    # --- 6. Майним ещё 1 блок, чтобы транзакция подтвердилась ---
    print("Майним блок для подтверждения...")
    try:
        res = node_post(node_url, "/mine", {
            "miner_address": miner_w.address,
            "broadcast": True,
        })
        print(f"  Блок #{res['block_index']}")
    except RuntimeError as e:
        print(f"[WARN] Майнинг подтверждения не удался: {e}")

    # --- 7. Назначаем казначея ---
    faucet_path = config.DATA_DIR / "faucet_8010.json"
    mgr = FaucetManager(faucet_path)
    mgr.set_treasury(args.treasury)
    print()
    print(f"Казначей назначен: {args.treasury}")
    print(f"  Файл: {faucet_path}")

    # --- 8. Финальная проверка баланса казначея ---
    time.sleep(1)
    bal2 = node_get(node_url, f"/balance/{treasury_w.address}")
    if bal2:
        print(f"Баланс казначея: {bal2.get('available_aix', 0)} AIX")

    print()
    print("Готово.")
    print("  Перезапусти ноды, чтобы казначей подхватился в API:")
    print("    .\\scripts\\stop_all.ps1")
    print("    .\\scripts\\run_all.ps1")
    print("  Потом проверь:")
    print("    .venv\\Scripts\\python.exe cli\\main.py faucet stats")
    return 0


if __name__ == "__main__":
    sys.exit(main())