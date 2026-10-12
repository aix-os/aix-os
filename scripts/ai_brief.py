"""
AIX OS — AI Brief.

Собрать бриф для AI из памяти + CONTEXT.md + текущего состояния системы.

Запуск:
    python scripts/ai_brief.py
    python scripts/ai_brief.py > AI_BRIEF.md

Потом скинь AI_BRIEF.md AI-ассистенту — он вспомнит всё.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from core.protocols.ai_memory import AIMemoryManager


def main():
    # 1. Бриф из памяти
    mem_path = ROOT / "data" / "ai_memory.json"
    mgr = AIMemoryManager(mem_path)
    brief_text = mgr.brief(max_critical=10, max_latest=20)

    # 2. CONTEXT.md
    context_path = ROOT / "CONTEXT.md"
    context_text = ""
    if context_path.exists():
        with open(context_path, "r", encoding="utf-8") as f:
            context_text = f.read()

    # 3. Собираем итог
    print("# 🧠 AIX OS — AI BRIEF")
    print()
    print(f"_Сгенерировано: {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    print()
    print("=" * 60)
    print()
    print("## 📋 CONTEXT.md")
    print()
    if context_text:
        print(context_text)
    else:
        print("_CONTEXT.md не найден. Создай его в корне проекта._")
    print()
    print("=" * 60)
    print()
    print(brief_text)
    print()
    print("=" * 60)
    print()
    print("## 📊 Статистика AI Memory")
    print()
    stats = mgr.stats()
    print(f"- Всего воспоминаний: {stats['total']}")
    print(f"- Сессий: {stats['sessions']}")
    print(f"- По типам: `{json.dumps(stats['by_kind'], ensure_ascii=False)}`")
    print(f"- По приоритетам: `{json.dumps(stats['by_priority'], ensure_ascii=False)}`")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())