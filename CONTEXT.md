### 2026-10-17 (сессия 5 — Мобильная нода и кэширование Python)

### 2026-10-18 (сессия 7 — Faable Cloud Node Fixed)

- **OOM на Faable побеждён:** Удалён 68 МБ `chain_A.json` из Git. Облачная нода стартует с `height=0` (генезис), чтобы не превышать лимит RAM. Локальная нода (85k+ блоков) остаётся на ПК.
- **Faable Startup Fixed:** Добавлен `faable.json` (`uvicorn main:app`) и `FAABLE-FALLBACK` в `network/server.py` (создаёт `app` из `PORT`).
- **Faucet Fixed:** Переписан на системный адрес `FAUCET` (в `SYSTEM_SENDERS`). Не требует кошелька `alice`. Выдаёт 1 AIX. Успешно протестирован на Faable: `{"status":"sent","amount_aix":1}`.
- **P2P на облаке:** Эндпоинты `/p2p/*` живы и готовы к UI.
- **Экономика:** Сложность 5, награда 0.005 AIX/блок на Faable.

**Следующий шаг:** Установить новый APK (с текстами 1 AIX и URL Faable) на телефон. Затем — P2P UI.

---


### 2026-10-18 (сессия 6 — P2P + per-block difficulty)

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
- `flutter analyze` падает на Windows с `FormatException` из-за кириллицы в пути `C:\Users\КОЛЮНЯ\...`. Решение — виртуальный диск `R:` через `subst`.
- `run_all.ps1` падает при наличии `--p2p` без аргумента. Проверять `args.p2p` после применения патча.
- Скрипт-патч `patch_p2p.py` может дать ложное "уже есть", если строка встречается в комментарии. Проверять через `Select-String`.

**Следующий шаг:** сборка APK через `R:` (обход кириллицы). Затем — применить патчи P2P и per-block difficulty к `aix-os-node` и запушить в Faable.

---

- **Мобильная нода**: интеграция Local/Remote полностью готова. Переключение, синк с внешней, майнинг, отправка транзакций и история работают.
- **Багфикс истории**: в `history_screen.dart` исправлено деление на `10^8` (вместо `10^18`). Суммы отображаются верно (`+50 AIX`, а не `+0.00000001`).
- **Багфикс комиссии**: `FEE_PERCENT` приведён к `0.1` (как в Python).
- **Ускорение Python-ноды**: `core/chain.py` переведён на кэширование (`_balances`, `_total_supply`, `_total_burned`). Раньше `/status` и `/balance` пересчитывали 85 000 блоков (таймаут 10 секунд), теперь отвечают за 0.01 сек. `storage/db.py` вызывает `_rebuild_cache()` при загрузке.
- ✅ Отправка AIX работает и на внешней, и на локальной ноде.
- ✅ Консоль Flutter больше не засыпает `TimeoutException`.

**Следующий шаг:** публикация (`git push`, Habr, VK/Telegram) или интеграция остальных протоколов (Swap, Contacts, SBT, PoC) в мобильный UI.