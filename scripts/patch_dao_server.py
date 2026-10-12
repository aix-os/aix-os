"""AIX OS — патч: проброс dao_manager в server.py (#13 -> #16).

Добавляет dao_manager последним позиционным аргументом в 4 вызова:
  - import_state (pull-loop, ~стр. 349)
  - export_state (/sync/state, ~стр. 1844)
  - apply_event  (/sync/state/event, ~стр. 1850)
  - import_state (ручной sync, ~стр. 1883)

Бэкап: network/server.py.bak
Запуск: .venv\\Scripts\\python.exe scripts\\patch_dao_server.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "network" / "server.py"


def replace_n(text: str, old: str, new: str, expected: int, label: str) -> str:
    n = text.count(old)
    if n != expected:
        print(f"[FAIL] {label}: ожидалось {expected}, найдено {n}")
        sys.exit(1)
    print(f"[ OK ] {label} (x{n})")
    return text.replace(old, new)


def patch(text: str) -> str:
    # 1. import_state в pull-loop + ручном sync (2 идентичных блока)
    text = replace_n(
        text,
        "                stats = import_state(state_data, gift_manager,\n"
        "                                     timelock_manager, sbt_manager,\n"
        "                                     inheritance_manager, id_manager,\n"
        "                                     burn_manager, contacts_manager,\n"
        "                                     swap_manager, poc_manager)\n",
        "                stats = import_state(state_data, gift_manager,\n"
        "                                     timelock_manager, sbt_manager,\n"
        "                                     inheritance_manager, id_manager,\n"
        "                                     burn_manager, contacts_manager,\n"
        "                                     swap_manager, poc_manager, dao_manager)\n",
        2,
        "import_state (pull-loop + sync)",
    )

    # 2. export_state в /sync/state
    text = replace_n(
        text,
        "        return export_state(gift_manager, timelock_manager, sbt_manager,\n"
        "                            inheritance_manager, id_manager, burn_manager,\n"
        "                            contacts_manager, swap_manager, poc_manager)\n",
        "        return export_state(gift_manager, timelock_manager, sbt_manager,\n"
        "                            inheritance_manager, id_manager, burn_manager,\n"
        "                            contacts_manager, swap_manager, poc_manager, dao_manager)\n",
        1,
        "export_state (/sync/state)",
    )

    # 3. apply_event в /sync/state/event
    text = replace_n(
        text,
        "        ok, msg = apply_event(req.event, gift_manager,\n"
        "                              timelock_manager, sbt_manager,\n"
        "                              inheritance_manager, id_manager,\n"
        "                              burn_manager, contacts_manager,\n"
        "                              swap_manager, poc_manager)\n",
        "        ok, msg = apply_event(req.event, gift_manager,\n"
        "                              timelock_manager, sbt_manager,\n"
        "                              inheritance_manager, id_manager,\n"
        "                              burn_manager, contacts_manager,\n"
        "                              swap_manager, poc_manager, dao_manager)\n",
        1,
        "apply_event (/sync/state/event)",
    )

    return text


def main():
    if not TARGET.exists():
        print(f"[FAIL] не найден {TARGET}")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")

    # Идемпотентность: если dao_manager уже последним аргументом — выходим
    if "swap_manager, poc_manager, dao_manager)" in src:
        print("[SKIP] server.py уже пропатчен")
        sys.exit(0)

    out = patch(src)

    bak = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, bak)
    print(f"[ OK ] бэкап -> {bak.name}")

    TARGET.write_text(out, encoding="utf-8")
    print(f"[ OK ] записан {TARGET}")
    print("[DONE] стоп/старт нод и тест синка")


if __name__ == "__main__":
    main()