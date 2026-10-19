from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.protocols.ai_memory import AIMemoryManager

mgr = AIMemoryManager(Path("data/ai_memory.json"))

items = [
    ("P2P-модуль готов: core/protocols/p2p.py + эндпоинты /p2p/* в server.py. Эскроу-адрес P2P-ESCROW добавлен в SYSTEM_SENDERS и SYSTEM_RECIPIENTS. Полный цикл протестирован: create → accept → confirm_paid → release → майнинг → покупатель получил AIX. Статусы: open/accepted/paid/completed/cancelled/disputed.",
     "MILESTONE", "CRITICAL", "p2p,backend,done"),

    ("Per-block difficulty внедрён (Python): поле Block.difficulty не входит в хэш, mine() запоминает, is_valid() проверяет каждый блок по его собственной сложности, from_dict() ставит default=1 для старых блоков. История 85k блоков сохранена, chain_valid=true. Файлы: core/block.py, core/chain.py, config.py, storage/db.py. Бэкапы *.pbd.bak.",
     "MILESTONE", "CRITICAL", "difficulty,blockchain,per-block"),

    ("Экономика финализирована: INITIAL_BLOCK_REWARD=0.005 AIX (= $0.5 при цене $100). Сложность: INITIAL=5, MIN=3, MAX=7. Целевое время блока ~10 сек на ПК. Факт: 10.72 сек/блок на Python. Награда в блоке 500000 сатоши.",
     "DECISION", "CRITICAL", "economy,mining,reward"),

    ("Dart (мобилка) обновлён под per-block difficulty и новую экономику: block.dart (поле difficulty, mine() запоминает, isValid() per-block, toJson/fromJson/copy), chain.dart (addBlock проставляет, isValid per-block), config_node.dart (MAX_DIFFICULTY=7, комментарии), mining_screen.dart (хардкод 50.0 → 0.005).",
     "MILESTONE", "CRITICAL", "flutter,dart,difficulty"),

    ("Flutter analyze падает с FormatException на Windows из-за кириллицы в пути (C:\\Users\\КОЛЮНЯ\\...). Кэш .dart_tool чистили — не помогло. Решение: работать через виртуальный диск R: (subst R: C:\\Users\\КОЛЮНЯ\\Desktop\\AIX-OS). Или собирать APK без analyze — flutter build apk обычно проходит.",
     "LEARNING", "IMPORTANT", "flutter,windows,cyrillic,build"),
]

for text, kind, prio, tags in items:
    m = mgr.add(text=text, kind=kind, priority=prio, tags=tags)
    print(f"+ [{kind}] {prio}: {text[:70]}...")

print(f"\n✅ Записано {len(items)}. Всего в памяти: {mgr.count()}")
