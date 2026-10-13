"""
AIX OS — сброс цепочки в чистый genesis.

Что делает:
1. Делает бэкап всей папки data/ в data_backup_YYYYMMDD_HHMMSS/
2. Удаляет ВСЕ данные блокчейна и протоколов:
   - chain_*.json
   - gifts_*.json, timelocks_*.json, sbt_*.json, inheritance_*.json
   - ids_*.json, burn_*.json, contacts_*.json, swap_*.json
   - poc_*.json, dao_*.json, peers_*.json
3. НЕ трогает:
   - data/wallets/*.wallet.json  (приватные ключи — остаются)
   - data/ai_memory.json         (AI Memory — остаётся)
4. Создаёт чистый genesis для нод A и B.

Запуск:
    .venv\\Scripts\\python.exe scripts\\reset_chain.py

Требует подтверждения y/N.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WALLETS = DATA / "wallets"
AI_MEMORY = DATA / "ai_memory.json"

# Что удаляем — по маске
KILL_PATTERNS = [
    "chain_*.json",
    "gifts_*.json",
    "timelocks_*.json",
    "sbt_*.json",
    "inheritance_*.json",
    "ids_*.json",
    "burn_*.json",
    "contacts_*.json",
    "swap_*.json",
    "poc_*.json",
    "dao_*.json",
    "peers_*.json",
]


def main() -> int:
    if not DATA.exists():
        print(f"[FATAL] Папка {DATA} не найдена")
        return 1

    # Собираем список файлов на удаление
    to_kill: list[Path] = []
    for pattern in KILL_PATTERNS:
        to_kill.extend(DATA.glob(pattern))

    print(f"Найдено файлов для удаления: {len(to_kill)}")
    for p in to_kill:
        print(f"  - {p.name}")

    # Защита: убедиться, что кошельки и память не попали в список
    for p in to_kill:
        if p == AI_MEMORY or WALLETS in p.parents:
            print(f"[FATAL] Ошибка: {p} нельзя удалять!")
            return 1

    print()
    print("Кошельки (сохранятся):")
    for w in sorted(WALLETS.glob("*.wallet.json")):
        print(f"  + {w.name}")

    print()
    print("AI Memory (сохранится):")
    if AI_MEMORY.exists():
        print(f"  + {AI_MEMORY.name}")
    else:
        print("  (нет)")

    print()
    ans = input("Сбросить цепочку в чистый genesis? [y/N] ").strip().lower()
    if ans not in ("y", "yes", "д", "да"):
        print("Отменено.")
        return 0

    # Бэкап всей data/ в отдельную папку
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = ROOT / f"data_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    for p in DATA.iterdir():
        if p.is_file():
            shutil.copy2(p, backup / p.name)
        elif p.is_dir() and p.name != "__pycache__":
            shutil.copytree(p, backup / p.name, dirs_exist_ok=True)
    print(f"\nБэкап: {backup.name}")

    # Удаляем
    killed = 0
    for p in to_kill:
        try:
            p.unlink()
            killed += 1
        except Exception as e:
            print(f"WARN: не удалось удалить {p.name}: {e}")

    print(f"Удалено: {killed} файлов")

    # Создаём чистый genesis для нод A и B
    sys.path.insert(0, str(ROOT))
    from core.chain import Blockchain
    from storage.db import ChainStorage

    for suffix in ("A", "B"):
        data_file = DATA / f"chain_{suffix}.json"
        storage = ChainStorage(str(data_file))
        chain = Blockchain()
        storage.save(chain)
        print(f"Создан genesis для ноды {suffix}: высота {chain.height()}")

    print()
    print("Сброс завершён. Чистый genesis создан.")
    print("   Перезапусти ноды:")
    print("     .\\scripts\\stop_all.ps1")
    print("     .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())