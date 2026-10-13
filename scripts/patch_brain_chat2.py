"""
Патч cli/main.py: срезаем ведущие '>' и '>>' из ввода Brain chat.

Идемпотентен. Бэкап: cli/main.py.chat2.bak.
Если якорь не найден — FATAL, файл не трогаем.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_brain_chat2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "main.py"

MARKER = "# Strip leading '>'"

OLD = '''        if not line:
            continue
        if line.lower() in ("exit", "quit", "q", "stop", "выход"):
            break
'''

NEW = '''        if not line:
            continue
        # Strip leading '>' or '>>' — привычка писать как в REPL
        while line.startswith(">"):
            line = line[1:].lstrip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q", "stop", "выход"):
            break
'''


def main() -> int:
    if not CLI.exists():
        print(f"[FATAL] {CLI} не найден")
        return 1

    src = CLI.read_text(encoding="utf-8")

    if MARKER in src:
        print("[cli/main.py] уже пропатчен — пропуск")
        return 0

    if OLD not in src:
        print("[FATAL] Не найден якорь ввода. Скинь мне cli/main.py.")
        return 1

    bak = CLI.with_suffix(CLI.suffix + ".chat2.bak")
    bak.write_bytes(CLI.read_bytes())
    print(f"[cli/main.py] backup -> {bak.name}")

    src = src.replace(OLD, NEW, 1)
    CLI.write_text(src, encoding="utf-8")

    print("[cli/main.py] OK: ведущие '>' срезаются")
    print()
    print("\u2705 Патч завершён.")
    print("   Проверь:")
    print("     .venv\\Scripts\\python.exe cli\\main.py brain chat --wallet alice")
    print("     > какая высота цепочки?    <-- с '>' теперь сработает")
    print("     > exit                      <-- тоже сработает")
    return 0


if __name__ == "__main__":
    sys.exit(main())