"""AIX OS — патч: /dao/all возвращает реальный count.

Бэкап: network/server.py.bak2 (не перетрём .bak от patch_dao_server)
Запуск: .venv\\Scripts\\python.exe scripts\\patch_dao_count.py
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "network" / "server.py"

OLD = (
    '        return {"count": limit, "proposals": [p.to_dict() for p in dao_manager.list_all(limit)]}'
)
NEW = (
    '        items = dao_manager.list_all(limit)\n'
    '        return {"count": len(items), "proposals": [p.to_dict() for p in items]}'
)


def main():
    if not TARGET.exists():
        print(f"[FAIL] не найден {TARGET}"); sys.exit(1)
    src = TARGET.read_text(encoding="utf-8")
    if "items = dao_manager.list_all(limit)" in src:
        print("[SKIP] уже пропатчено"); sys.exit(0)
    if src.count(OLD) != 1:
        print(f"[FAIL] ожидалось 1 совпадение, найдено {src.count(OLD)}"); sys.exit(1)
    out = src.replace(OLD, NEW, 1)
    bak = TARGET.with_suffix(".py.bak2")
    shutil.copy2(TARGET, bak)
    print(f"[ OK ] бэкап -> {bak.name}")
    TARGET.write_text(out, encoding="utf-8")
    print(f"[ OK ] записан {TARGET}")
    print("[DONE] перезапусти ноды чтобы подхватилось (правило №3)")


if __name__ == "__main__":
    main()