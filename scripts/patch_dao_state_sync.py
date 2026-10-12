"""AIX OS — патч: DAO в state_sync.py (#13 -> #16).

Добавляет:
  1. import Proposal
  2. dao_manager в сигнатуры export_state / import_state / apply_event
  3. export dao_proposals + import dao_proposals (bulk)
  4. make_dao_event()
  5. case "dao_proposal" в apply_event

Бэкап: core/protocols/state_sync.py.bak
Запуск: .venv\\Scripts\\python.exe scripts\\patch_dao_state_sync.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "core" / "protocols" / "state_sync.py"


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        print(f"[FAIL] {label}: ожидалось 1 совпадение, найдено {n}")
        sys.exit(1)
    print(f"[ OK ] {label}")
    return text.replace(old, new, 1)


def _replace_n(text: str, old: str, new: str, expected: int, label: str) -> str:
    n = text.count(old)
    if n != expected:
        print(f"[FAIL] {label}: ожидалось {expected}, найдено {n}")
        sys.exit(1)
    print(f"[ OK ] {label} (x{n})")
    return text.replace(old, new)


def patch(text: str) -> str:
    # 1. Импорт Proposal
    text = _replace_once(
        text,
        "from core.protocols.poc import Contribution, RewardPool\n",
        "from core.protocols.poc import Contribution, RewardPool\n"
        "from core.governance.dao import Proposal\n",
        "import Proposal",
    )

    # 2. Сигнатуры export_state и import_state — swap/poc -> swap/poc/dao
    text = _replace_n(
        text,
        "swap_manager=None, poc_manager=None) -> dict:",
        "swap_manager=None, poc_manager=None, dao_manager=None) -> dict:",
        2,
        "сигнатуры export_state/import_state",
    )

    # 3. apply_event — сигнатура
    text = _replace_once(
        text,
        "swap_manager=None, poc_manager=None) -> tuple:",
        "swap_manager=None, poc_manager=None, dao_manager=None) -> tuple:",
        "сигнатура apply_event",
    )

    # 4. export_state — выгрузить dao_proposals
    text = _replace_once(
        text,
        '        result["poc_pool"] = poc_manager.pool.to_dict()\n'
        "    return result\n",
        '        result["poc_pool"] = poc_manager.pool.to_dict()\n'
        "    if dao_manager is not None:\n"
        '        result["dao_proposals"] = dao_manager.export_all()\n'
        "    return result\n",
        "export_state: dao_proposals",
    )

    # 5. added/skipped словари — добавить счётчик dao_proposals
    text = _replace_n(
        text,
        '             "poc_contributions": 0}',
        '             "poc_contributions": 0, "dao_proposals": 0}',
        2,
        "added/skipped: dao_proposals",
    )

    # 6. import_state — bulk-цикл по dao_proposals (перед блоком # Save)
    text = _replace_once(
        text,
        "    # Save\n",
        "    # DAO\n"
        "    if dao_manager is not None:\n"
        '        for item in data.get("dao_proposals", []):\n'
        "            try:\n"
        "                ok, msg = dao_manager.import_proposal(item)\n"
        '                if ok and msg in ("добавлен", "обновлён", "голоса обновлены"):\n'
        '                    added["dao_proposals"] += 1\n'
        "                else:\n"
        '                    skipped["dao_proposals"] += 1\n'
        "            except Exception as e:\n"
        '                print(f"WARN: import dao_proposal: {e}")\n'
        "\n"
        "    # Save\n",
        "import_state: dao bulk",
    )

    # 7. make_dao_event
    text = _replace_once(
        text,
        "def make_poc_pool_event(pool: RewardPool) -> dict:\n"
        '    return {"kind": "poc_pool", "data": pool.to_dict()}\n',
        "def make_poc_pool_event(pool: RewardPool) -> dict:\n"
        '    return {"kind": "poc_pool", "data": pool.to_dict()}\n'
        "\n"
        "\n"
        "def make_dao_event(proposal: Proposal) -> dict:\n"
        '    return {"kind": "dao_proposal", "data": proposal.to_dict()}\n',
        "make_dao_event",
    )

    # 8. apply_event — case dao_proposal
    text = _replace_once(
        text,
        '        return False, f"неизвестный kind: {kind}"',
        '        if kind == "dao_proposal":\n'
        "            if dao_manager is None:\n"
        '                return False, "dao manager недоступен"\n'
        "            ok, msg = dao_manager.import_proposal(data)\n"
        '            return ok, f"dao_proposal: {msg}"\n'
        "\n"
        '        return False, f"неизвестный kind: {kind}"',
        'apply_event: case "dao_proposal"',
    )

    return text


def main():
    if not TARGET.exists():
        print(f"[FAIL] не найден {TARGET}")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")

    marker = "dao_manager"
    if marker in src:
        print("[SKIP] файл уже пропатчен (найден dao_manager)")
        sys.exit(0)

    out = patch(src)

    bak = TARGET.with_suffix(".py.bak")
    shutil.copy2(TARGET, bak)
    print(f"[ OK ] бэкап -> {bak.name}")

    TARGET.write_text(out, encoding="utf-8")
    print(f"[ OK ] записан {TARGET}")
    print("[DONE] перезапусти ноды: .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")


if __name__ == "__main__":
    main()