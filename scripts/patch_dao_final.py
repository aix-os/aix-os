"""AIX OS — финальный патч DAO: count + лог State."""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"

def main():
    src = SERVER.read_text(encoding="utf-8")
    changed = False

    # Фикс 1: /dao/all count
    old1 = '        return {"count": limit, "proposals": [p.to_dict() for p in dao_manager.list_all(limit)]}'
    new1 = ('        items = dao_manager.list_all(limit)\n'
            '        return {"count": len(items), "proposals": [p.to_dict() for p in items]}')
    if "items = dao_manager.list_all(limit)" in src:
        print("[SKIP] dao_all count уже пофикшен")
    elif src.count(old1) == 1:
        src = src.replace(old1, new1, 1)
        print("[ OK ] dao_all: count = len(items)")
        changed = True
    else:
        print(f"[FAIL] dao_all: найдено {src.count(old1)} совпадений (ожидалось 1)")
        sys.exit(1)

    # Фикс 2: добавить dao_proposals в лог State
    old2 = '                 f"+{a.get(\'swap_pools\', 0)} swap_pools, "\n'
    new2 = ('                 f"+{a.get(\'swap_pools\', 0)} swap_pools, "\n'
            '                 f"+{a.get(\'dao_proposals\', 0)} dao, "\n')
    if "+{a.get('dao_proposals', 0)} dao, " in src:
        print("[SKIP] State-лог dao уже есть")
    elif src.count(old2) == 1:
        src = src.replace(old2, new2, 1)
        print("[ OK ] State-лог: dao добавлен")
        changed = True
    else:
        print(f"[WARN] State-лог: найдено {src.count(old2)} совпадений, пропуск")

    if changed:
        bak = SERVER.with_suffix(".py.bak4")
        shutil.copy2(SERVER, bak)
        print(f"[ OK ] бэкап -> {bak.name}")
        SERVER.write_text(src, encoding="utf-8")
        print("[DONE] перезапусти ноды: .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")
    else:
        print("[DONE] нечего менять")

if __name__ == "__main__":
    main()
