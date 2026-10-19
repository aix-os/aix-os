from pathlib import Path
p = Path("CONTEXT.md")
c = p.read_text(encoding="utf-8")

entry = """### 2026-10-18 (сессия 6 — P2P + per-block difficulty)

**P2P-модуль готов (полный цикл протестирован):**
- Новый файл `core/protocols/p2p.py` — эскроу-менеджер, статусы open/accepted/paid/completed/cancelled/disputed.
- Эндпоинты `/p2p/*` в `network/server.py` (create, list, get, accept, confirm_paid, release, cancel, dispute, chat, stats).
- `P2P-ESCROW` добавлен в `SYSTEM_SENDERS` и `SYSTEM_RECIPIENTS` в `core/transaction.py`.
- Полный цикл: airi заблокировала 100 AIX → ордер P2P-PANZ-VWVL (8500 ₽/AIX) → bob купил 10 AIX → оплатил (85 000 ₽) → продавец release → блок замайнен → bob получил +10 AIX, эскроу уменьшился до 90.
- Скрипты теста: `scripts/test_p2p_flow.py`, `scripts/test_p2p_flow2.py`.

**Per-block difficulty (Python + Dart):**
- Поле `Block.difficulty` (НЕ входит в хэш). `mine()` запоминает сложность, `is_valid()` проверяет блок по его собственной.
- Старые блоки без поля → `difficulty=1`. Новые → текущая (старт 5).
- `chain_valid=true` после патча — вся история 85k блоков сохранена.
- Бэкапы: `*.pbd.bak`.
- Dart-зеркало: `block.dart`, `chain.dart`, `config_node.dart`, `mining_screen.dart` (хардкод 50.0 → 0.005).

**Экономика:**
- `INITIAL_BLOCK_REWARD = 0.005 AIX` ($0.5 при $100).
- Сложность: `INITIAL=5, MIN=3, MAX=7`. Факт: 10.72 сек/блок на ПК.

**Грабли:**
- `flutter analyze` падает на Windows с `FormatException` из-за кириллицы в пути `C:\\Users\\КОЛЮНЯ\\...`. Решение — виртуальный диск `R:` через `subst`.
- `run_all.ps1` падает при наличии `--p2p` без аргумента. Проверять `args.p2p` после применения патча.
- Скрипт-патч `patch_p2p.py` может дать ложное "уже есть", если строка встречается в комментарии. Проверять через `Select-String`.

**Следующий шаг:** сборка APK через `R:` (обход кириллицы). Затем — применить патчи P2P и per-block difficulty к `aix-os-node` и запушить в Faable.

---

"""

# Вставляем после первой строки-заголовка
lines = c.split("\n", 1)
if len(lines) == 2:
    new_c = lines[0] + "\n\n" + entry + lines[1]
else:
    new_c = entry + c

p.write_text(new_c, encoding="utf-8")
print("OK: CONTEXT.md updated")
