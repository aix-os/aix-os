"""
AIX OS — создание кошельков founder и treasury.

- founder   — личный кошелёк основателя (10% от swap-комиссии сюда)
- treasury  — фонд проекта, управляется через DAO

Оба кошелька создаются один раз. Если уже существуют — показывает адреса.

Запуск:
    .venv\\Scripts\\python.exe scripts\\setup_founder_wallets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.wallet import Wallet  # noqa: E402


def ensure(name: str, description: str) -> str:
    if Wallet.exists(name):
        w = Wallet.load(name)
        print(f"[{name}] уже существует")
        print(f"   Описание: {description}")
        print(f"   Адрес:    {w.address}")
        return w.address
    w = Wallet.create(name)
    w.save()
    print(f"[{name}] СОЗДАН")
    print(f"   Описание: {description}")
    print(f"   Адрес:    {w.address}")
    print(f"   Файл:     data/wallets/{name}.wallet.json")
    return w.address


def main() -> int:
    print("=" * 60)
    print("  AIX OS — системные кошельки")
    print("=" * 60)
    print()

    founder_addr = ensure("founder",
        "Основатель проекта. Сюда идёт 0.1% с каждого swap.")
    print()
    treasury_addr = ensure("treasury",
        "Фонд проекта. Управляется DAO. Сюда идут комиссии сети.")
    print()

    print("=" * 60)
    print("  Готово")
    print("=" * 60)
    print()
    print("Запиши в память AIX OS:")
    print()
    print("   .venv\\Scripts\\python.exe cli\\main.py ai remember "
          f"\"Созданы системные кошельки: founder={founder_addr}, "
          f"treasury={treasury_addr}. Revenue share: 0.1% с swap-комиссии идёт "
          "founder, 0.2% — LP-держателям. Fee за send 0.1% идёт майнеру блока. "
          "Treasury управляется через DAO (кворум 30%, порог 50%, макс выплата 10%).\" "
          "--kind=DECISION --priority=CRITICAL --tags=economy,founder,treasury")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())