"""
Патч config.py — устанавливает DIFFICULTY = 5.

Difficulty в AIX OS = количество ведущих нулей в hex-хеше блока.
  1 → 16 попыток в среднем
  2 → 256
  3 → 4096
  4 → 65 536
  5 → ~1 000 000
  6 → ~16 000 000

На процессоре Python (быстро ~2000–5000 хешей/сек) сложность 5 даёт
в среднем блок за ~5 минут, сложность 6 — за час+.

Мы ставим 5, чтобы попасть примерно в 20 минут с запасом и
дать возможность поднять до 6 позже, когда хешрейт вырастет.

Идемпотентен. Бэкап: config.py.diff.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_difficulty.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.py"

TARGET_DIFFICULTY = 5


def main() -> int:
    if not CONFIG.exists():
        print(f"[FATAL] {CONFIG} не найден")
        return 1

    src = CONFIG.read_text(encoding="utf-8")

    # Ищем строку вида: DIFFICULTY = 3   (с возможным комментарием)
    pattern = re.compile(r"^(DIFFICULTY\s*=\s*)(\d+)(.*)$", re.MULTILINE)
    match = pattern.search(src)

    if not match:
        print("[FATAL] В config.py не найдена строка 'DIFFICULTY = N'.")
        print("  Пришли мне config.py — пересчитаю якорь.")
        return 1

    current = int(match.group(2))
    print(f"Текущая сложность: {current}")

    if current == TARGET_DIFFICULTY:
        print(f"Сложность уже {TARGET_DIFFICULTY} — пропуск.")
        return 0

    bak = CONFIG.with_suffix(".py.diff.bak")
    bak.write_bytes(CONFIG.read_bytes())
    print(f"Бэкап: {bak.name}")

    # Заменяем только число
    new_src = pattern.sub(
        lambda m: f"{m.group(1)}{TARGET_DIFFICULTY}{m.group(3)}",
        src,
        count=1,
    )
    CONFIG.write_text(new_src, encoding="utf-8")

    print(f"OK: DIFFICULTY {current} -> {TARGET_DIFFICULTY}")
    print()
    print("Что произойдёт:")
    print("  • Новые блоки будут искаться дольше (~20 минут на CPU)")
    print("  • Уже созданные блоки не переделываются")
    print("  • Майнинг можно продолжить как обычно: mine_founder.py")
    print()
    print("Перезапусти ноды, чтобы изменения подхватились:")
    print("  .\\scripts\\stop_all.ps1")
    print("  .\\scripts\\run_all.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())