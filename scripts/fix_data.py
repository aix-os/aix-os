"""
AIX OS — Одноразовый фикс данных после багов #1 и #2.

Что делает:
1. Во всех data/chain_*.json — чистит mempool от stale-tx
   (тех, что уже есть в цепочке).
2. В data/poc_*.json — синхронизирует pool между нодами
   (total_donated, total_paid, donations, payouts).

Запуск:
    python scripts/fix_data.py

Перед изменением создаёт .bak-файлы рядом с оригиналами.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
DATA = ROOT / "data"


def tx_key(tx: dict) -> tuple:
    """Уникальный ключ транзакции для сравнения (без tx_id)."""
    return (
        tx.get("sender", ""),
        tx.get("recipient", ""),
        tx.get("amount", 0),
        tx.get("timestamp", 0),
    )


def fix_chain_mempool(path: Path) -> None:
    """Чистит stale-tx из mempool в chain_*.json"""
    if not path.exists():
        print(f"  ⏭️  {path.name}: не найден")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chain = data.get("chain", [])
    mempool = data.get("mempool", [])

    if not mempool:
        print(f"  ✅ {path.name}: mempool уже пуст")
        return

    # Собираем ключи всех tx из цепочки
    included = set()
    for block in chain:
        for tx in block.get("transactions", []):
            included.add(tx_key(tx))

    # Фильтруем mempool
    clean = [tx for tx in mempool if tx_key(tx) not in included]
    removed = len(mempool) - len(clean)

    if removed == 0:
        print(f"  ✅ {path.name}: stale-tx не найдено (в mempool: {len(mempool)})")
        return

    # Бэкап
    backup = path.with_suffix(".json.bak")
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    data["mempool"] = clean
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  🔧 {path.name}: удалено {removed} stale-tx "
          f"(осталось: {len(clean)}, бэкап: {backup.name})")


def merge_pool(src_pool: dict, dst_pool: dict) -> tuple:
    """
    Merge двух пулов по уникальным ключам.
    Возвращает (merged_pool, changed).
    """
    merged_donated = dst_pool.get("total_donated", 0)
    merged_paid = dst_pool.get("total_paid", 0)
    merged_donations = list(dst_pool.get("donations", []))
    merged_payouts = list(dst_pool.get("payouts", []))

    changed = False

    # Сливаем донаты
    existing_don_keys = {(d.get("address"), d.get("time")) for d in merged_donations}
    for d in src_pool.get("donations", []):
        key = (d.get("address"), d.get("time"))
        if key not in existing_don_keys:
            merged_donations.append(d)
            merged_donated += d.get("amount", 0)
            existing_don_keys.add(key)
            changed = True

    # Сливаем выплаты
    existing_pay_keys = {(p.get("address"), p.get("contribution_id"))
                         for p in merged_payouts}
    for p in src_pool.get("payouts", []):
        key = (p.get("address"), p.get("contribution_id"))
        if key not in existing_pay_keys:
            merged_payouts.append(p)
            merged_paid += p.get("amount", 0)
            existing_pay_keys.add(key)
            changed = True

    merged = {
        "total_donated": merged_donated,
        "total_paid": merged_paid,
        "donations": merged_donations,
        "payouts": merged_payouts,
    }
    return merged, changed


def fix_poc_pools() -> None:
    """Синхронизирует pool между всеми data/poc_*.json."""
    poc_files = sorted(DATA.glob("poc_*.json"))
    if len(poc_files) < 2:
        print(f"  ⏭️  Найдено {len(poc_files)} файлов poc_*.json, нечего синхронизировать")
        return

    # Загружаем все пулы
    pools = []
    for f in poc_files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        pools.append((f, d))

    # Последовательно мёржим все в эталон
    ref_file, ref_data = pools[0]
    ref_pool = ref_data.get("pool", {})
    total_changed = False

    for f, d in pools[1:]:
        other_pool = d.get("pool", {})
        merged, changed = merge_pool(other_pool, ref_pool)
        if changed:
            ref_pool = merged
            total_changed = True

    if not total_changed:
        print(f"  ✅ Все PoC-пулы уже синхронизированы")
        return

    # Записываем эталон во все файлы
    for f, d in pools:
        old_pool = d.get("pool", {})
        old_paid = old_pool.get("total_paid", 0)
        old_don = old_pool.get("total_donated", 0)

        # Бэкап
        backup = f.with_suffix(".json.bak")
        with open(backup, "w", encoding="utf-8") as fp:
            json.dump(d, fp, ensure_ascii=False, indent=2)

        d["pool"] = ref_pool
        with open(f, "w", encoding="utf-8") as fp:
            json.dump(d, fp, ensure_ascii=False, indent=2)

        new_paid = ref_pool["total_paid"]
        new_don = ref_pool["total_donated"]
        print(f"  🔧 {f.name}: donated {old_don / 10**18:.0f}→{new_don / 10**18:.0f} AIX, "
              f"paid {old_paid / 10**18:.0f}→{new_paid / 10**18:.0f} AIX "
              f"(бэкап: {backup.name})")


def main():
    print("🔧 AIX OS — Одноразовый фикс данных")
    print("=" * 55)

    if not DATA.exists():
        print(f"❌ Папка {DATA} не найдена. Запусти из корня проекта.")
        return 1

    # Фикс 1: mempool во всех chain_*.json
    print("\n📦 Фикс mempool (stale-tx в цепочках):")
    for chain_file in sorted(DATA.glob("chain_*.json")):
        fix_chain_mempool(chain_file)

    # Фикс 2: PoC pools
    print("\n🧬 Фикс PoC-пула (merge между нодами):")
    fix_poc_pools()

    print("\n" + "=" * 55)
    print("✅ Готово. Запусти ноды: .\\scripts\\run_all.ps1")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())