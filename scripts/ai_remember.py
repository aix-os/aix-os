"""AIX OS — записать воспоминание AI.

Примеры:
    python scripts/ai_remember.py "Пофиксил баг с mempool" --kind=BUG_FIXED --priority=IMPORTANT --tags=mempool,chain
    python scripts/ai_remember.py "Начало сессии" --kind=SESSION_START --priority=NORMAL
    python scripts/ai_remember.py          # интерактивный ввод
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from core.protocols.ai_memory import (
    AIMemoryManager, KINDS, PRIORITIES, KIND_EMOJI, PRIORITY_EMOJI,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Записать воспоминание в AI Memory (AIX OS)")
    p.add_argument("text", nargs="?", help="Текст воспоминания")
    p.add_argument("--kind", default="THOUGHT", choices=KINDS)
    p.add_argument("--priority", default="NORMAL", choices=PRIORITIES)
    p.add_argument("--tags", default="", help="Теги через запятую: mempool,chain,fix")
    p.add_argument("--session", default=None, help="ID сессии (по умолчанию — текущая дата)")
    p.add_argument("--chain-ref", default="", help="txid / высота блока, если есть")
    p.add_argument("--file", default=str(ROOT / "data" / "ai_memory.json"))
    args = p.parse_args()

    text = args.text
    if not text:
        print("Введи текст воспоминания (Ctrl+Z / Ctrl+D — конец):")
        text = sys.stdin.read().strip()
    if not text:
        print("❌ Пустой текст. Ничего не записано.", file=sys.stderr)
        return 2

    mgr = AIMemoryManager(Path(args.file))
    try:
        mem = mgr.add(
            text=text, kind=args.kind, priority=args.priority,
            tags=args.tags, session=args.session, chain_ref=args.chain_ref,
        )
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    ke = KIND_EMOJI.get(mem.kind, "•")
    pe = PRIORITY_EMOJI.get(mem.priority, "•")
    print(f"✅ Записано: {ke} [{mem.kind}] {pe} {mem.priority}")
    print(f"   {mem.text}")
    print(f"   session={mem.session} ts={mem.ts} hash={mem.hash[:10]}")
    print(f"   всего в памяти: {mgr.count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())