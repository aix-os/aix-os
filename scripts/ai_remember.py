"""
AIX OS — AI Remember.

Записать воспоминание в AIX Memory.

Запуск:
    python scripts/ai_remember.py "Заголовок" --body="Подробности" --kind=MILESTONE --priority=IMPORTANT --tags=mempool,poc

Примеры:
    python scripts/ai_remember.py "Начало сессии 4"
    python scripts/ai_remember.py "Пофиксил баг с mempool" --kind=BUG_FIXED --priority=IMPORTANT
    python scripts/ai_remember.py "План на сессию" --kind=IDEA --body="Допилить DAO"
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from core.protocols.ai_memory import AIMemoryManager, KINDS, PRIORITIES


def main():
    p = argparse.ArgumentParser(description="AIX OS — AI Remember")
    p.add_argument("title", help="Заголовок воспоминания")
    p.add_argument("--body", "-b", default="", help="Подробности")
    p.add_argument("--kind", "-k", default="THOUGHT",
                   choices=list(KINDS.keys()), help="Тип воспоминания")
    p.add_argument("--priority", "-p", default="NORMAL",
                   choices=list(PRIORITIES.keys()), help="Приоритет")
    p.add_argument("--tags", "-t", default="", help="Теги через запятую")
    p.add_argument("--session", "-s", default="", help="ID сессии (по умолчанию дата)")
    p.add_argument("--data", "-d", default=str(ROOT / "data" / "ai_memory.json"),
                   help="Путь к файлу памяти")

    args = p.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    mgr = AIMemoryManager(args.data)
    mem = mgr.remember(
        title=args.title,
        body=args.body,
        kind=args.kind,
        priority=args.priority,
        tags=tags,
        session_id=args.session,
    )

    print(f"✅ Запомнено:")
    print(f"   ID:        {mem.id}")
    print(f"   Тип:       {mem.emoji()} {mem.kind} / {mem.priority_emoji()} {mem.priority}")
    print(f"   Заголовок: {mem.title}")
    if mem.body:
        print(f"   Тело:      {mem.body}")
    if mem.tags:
        print(f"   Теги:      {', '.join(mem.tags)}")
    print(f"   Всего:     {len(mgr)} воспоминаний")
    return 0


if __name__ == "__main__":
    sys.exit(main())