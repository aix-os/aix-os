# 🧠 AIX OS — CONTEXT для AI-ассистента

> **Как пользоваться:** в начале новой AI-сессии скинь этот файл целиком.
> После работы — обнови блоки «Состояние» и «Журнал».

---

## 1. Что это за проект

**AIX OS** — децентрализованная операционная система для жизни.
Собственный блокчейн (PoW, ECDSA secp256k1, Base58Check-адреса `AIX...`).
Тикер: **AIX**. Максимум: 21 000 000. Pre-mine: 0%.

Кредо: *«Технологии должны делать людей счастливее, а не богаче.»*
Слоган: *«Империя начинается с тебя.»*

**Стек:**
- Python 3.11 + FastAPI + Uvicorn + ECDSA + base58
- Web Wallet — чистый HTML/JS + Chart.js
- CLI — argparse + colorama + tabulate
- Telegram-бот — python-telegram-bot
- Мобильное — Flutter (собрано под Windows)

---

## 2. Текущее состояние

- **Высота цепочки:** 17
- **Ноды:**
  - A: порт 8010, файл `data/chain_A.json`
  - B: порт 8011, файл `data/chain_B.json`
- **Майнер:** `AIXTYTXqm8WBFE6iX9UCFsp3qbF3VoKjAMxG8`
- **Основатель:** `alice` (`AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2`)
- **Наследники:** `bob` (60%) + `carol` (40%) — DMS сработал (triggered)
- **PoC:** 150 AIX внесли, 150 выплачено, 1 вклад в pending
- **Swap:** 1 пул (AIX-SIM/USDT-SIM, 1000/500, LP=707.1)
- **SBT:** 2 медали (FOUNDER у alice, EARLY_BIRD у bob)
- **Burn:** 1 артефакт (COM-001, Уголёк #1)
- **Contacts:** 1 хеш номера привязан к alice
- **Последние фиксы:**
  - `chain.py::replace_chain()` — mempool cleanup
  - `poc.py::import_pool()` — merge по ключам
  - `storage/db.py::load()` — автоочистка stale-tx
  - `scripts/fix_data.py` — одноразовый фикс данных

---

## 3. Карта файлов

### 🔴 Ядро (не трогать без причины)
- `config.py` — все константы проекта
- `core/block.py` — блок, PoW, merkle
- `core/chain.py` — цепочка, `add_block`, `replace_chain`, `get_balance`
- `core/transaction.py` — tx, ECDSA-подпись, системные sender'ы
- `core/mempool.py` — очередь tx
- `core/wallet.py` — ключи, подпись
- `storage/db.py` — ChainStorage (JSON + mempool + автоочистка)

### 🟡 Протоколы (`core/protocols/`)
- `gift_link.py` — подарки по коду `AIX-XXXX-XXXX`
- `time_lock.py` — капсулы до даты `unlock_at`
- `sbt.py` — медали, репутация (common=1, uncommon=3, rare=10, legendary=50)
- `lottery.py` — 1 из `LOTTERY_CHANCE` блоков даёт 100 AIX
- `dead_mans_switch.py` — наследие, `timeout_days`, `check_in`, `trigger`
- `aix_id.py` — `@имя` → адрес, профиль
- `burn_to_mint.py` — 5 уровней артефактов (COMMON..MYTHIC)
- `contacts.py` — хеш номера → адрес, `PHONE_SALT = "AIX-OS-PHONE-v1"`
- `swap.py` — AMM, x*y=k, fee 0.3%, защита от опустошения (5% от initial)
- `poc.py` — Proof of Contribution, уровни MICRO/SMALL/MEDIUM/LARGE
- `state_sync.py` — экспорт/импорт состояния, `apply_event`, `make_*_event`

### 🌐 Сеть
- `network/server.py` — FastAPI, ~1761 строк, все эндпоинты
- `network/peer.py` — клиент к другой ноде
- `network/peer_manager.py` — реестр пиров

### 💻 Интерфейсы
- `cli/main.py` — CLI, ~2072 строки
- `web/index.html` — Web Wallet, ~833 строки
- `integrations/telegram/bot.py` — Telegram-бот
- `mobile/flutter_app/lib/` — Flutter (7 экранов)

### 📜 Документы
- `README.md`, `ROADMAP.md`, `docs/WHITEPAPER.md`
- `docs/index.html` и `web/landing/index.html` — лендинг (дубли!)

### 🛠️ Скрипты (`scripts/`)
- `run_all.ps1` — запуск 2 нод + web
- `stop_all.ps1` — остановка
- `backup.ps1` — бэкап data/
- `mine_batch.ps1` — пакетный майнинг
- `faucet.py` — раздача тестовых AIX
- `init_genesis.py` — генезис с нуля
- `reset_db.py` — сброс данных
- `debug_lottery.py` — отладка лотереи
- `fix_data.py` — одноразовый фикс (mempool + PoC)

---

## 4. Известные баги (для истории)

### ✅ Баг #1 — Stale-tx в mempool (ИСПРАВЛЕНО)
**Симптом:** tx `Alice→Bob 5 AIX` одновременно в блоке #11 и в mempool B.
**Причина:** `chain.py::replace_chain()` не чистил mempool.
**Фикс:** `self.mempool.remove_many(list(new_tx_ids))` в `replace_chain`.

### ✅ Баг #2 — Рассинхрон PoC-пула (ИСПРАВЛЕНО)
**Симптом:** `poc_8010.json` → `total_paid=150`, `poc_8011.json` → `total_paid=0`.
**Причина:** `poc.py::import_pool()` сравнивал только `total_donated`.
**Фикс:** merge по уникальным ключам (donations + payouts).

### 🟡 Прочее
- `tests/*` — 5 файлов по 0 байт. **Тестов нет.**
- `core/consensus/*` (pow/pos/poc/dag) — пустые
- `core/governance/*` (dao/constitution/public/veto) — пустые
- `core/justice/*` (jury/appeals) — пустые
- `crypto/zk`, `crypto/homomorphic`, `crypto/cold_storage`, `crypto/recovery` — пустые
- `crypto/dilithium.py` — пустой (PQC)
- `ai/*` — 14 папок пустые (ИИ пока не в ядре)
- `apps/*` — arena, art, dating, dreams, radio, university, whisper — пустые
- `network/mesh/*` — bluetooth.py, lora.py — пустые
- `integrations/*` (кроме telegram) — banks, carbon, games, genome,
  gosuslugi, green, health, iot, nfc, sbp — пустые
- `web/app.js`, `web/styles.css` — пустые (вся логика в index.html)
- `docs/ARCHITECTURE.md`, `TOKENOMICS.md`, `LEGAL.md`, `PRIVACY.md`,
  `SECURITY.md`, `CONTACTS_PROTOCOL.md`, `AIX_OS_SPEC.md` — пустые

---

## 5. Ключевые решения (не менять!)

| Что | Значение | Почему |
|-----|----------|--------|
| Кривая | ECDSA secp256k1 | Как Bitcoin/Ethereum |
| Адрес | `AIX` + Base58Check(version 0x41 + hash160) | Стандарт Bitcoin |
| Хеш | Двойной SHA-256 | Защита от length-extension |
| Награда за блок | 50 AIX, халвинг каждые 210k | Как Bitcoin |
| Сложность | Пересчёт каждые 10 блоков, MAX=10 | MVP-ограничение |
| Майнер | `COINBASE` (системный sender) | Как Bitcoin |
| Сжигание | `recipient="BURN"` уменьшает supply | Для дефляции |
| PoC фонд | `POC-POOL` (системный) | Как COINBASE |
| Phone salt | `AIX-OS-PHONE-v1` | **Не менять!** Иначе хеши сломаются |
| AMM | x*y=k, fee 0.3%, min 5% от initial | Как Uniswap V2 |
| PoC уровни | MICRO≤100(1), SMALL≤1000(2), MEDIUM≤5000(3), LARGE(5) | Баланс |

---

## 6. TODO (обновлять)

- [ ] Наполнить `core/governance/dao.py` — PoC → DAO с голосованием
- [ ] Наполнить `ai/brain/` — локальная LLM (Ollama) для AIX-ассистента
- [ ] Наполнить `crypto/zk/` — ZK-proofs для приватных tx
- [ ] Наполнить `network/mesh/lora.py` — оффлайн-сеть
- [ ] Написать тесты в `tests/` (block, chain, transaction, wallet, crypto)
- [ ] Почистить репо: убрать `data_backup_*`, `web_backup/`,
      `*.backup`, `project-tree.txt`, `alice_qr.png`
- [ ] Обновить статистику на лендинге (229 файлов → актуально)
- [ ] Исправить commit `b736970` (placeholder message)
- [ ] Довести Flutter-приложение до Android APK

---

## 7. Как запускать

```powershell
# Активировать venv
.venv\Scripts\Activate.ps1

# Запустить сеть (2 ноды + web)
.\scripts\run_all.ps1

# Остановить всё
.\scripts\stop_all.ps1

# Бэкап
.\scripts\backup.ps1 my_label

# Пакетный майнинг
.\scripts\mine_batch.ps1 alice 50

# Починить данные после багов
python scripts/fix_data.py

# Статус ноды
python cli/main.py node status
```

**Порты:**
- Node A: `http://localhost:8010`
- Node B: `http://localhost:8011`
- Web Wallet: `http://localhost:9000`
- Swagger: `http://localhost:8010/docs`

---

## 8. Журнал сессий

### 2026-10-12 (сессия 3)
**Сделано:**
- Полный dump проекта (217 файлов, 23 632 строки)
- Патч `chain.py::replace_chain()` — mempool cleanup
- Патч `poc.py::import_pool()` — merge по ключам
- Патч `storage/db.py::load()` — автоочистка stale-tx
- Создан `scripts/fix_data.py`
- Создан `CONTEXT.md`

**Открыто:**
- Запустить `python scripts/fix_data.py`
- Закоммитить изменения

### 2026-10-11 (сессия 2)
Загрузка проекта, первый обзор.

---

## 9. Правила работы с AI

1. **В начале сессии** — скинуть `CONTEXT.md` + 3-5 горячих файлов.
2. **В конце сессии** — обновить разделы 2, 6, 8.
3. **Не показывать** AI файлы `*.wallet.json` (приватные ключи).
4. **Патчи в `core/` и `crypto/`** — предупреждать явно.
5. **Формат ответа AI** — целые файлы или точные пути, без кусков кода
   (пользователь копирует файл целиком в редактор).

---

## 10. Как обновлять этот файл

После каждой сессии AI даёт блок:

```
📝 ОБНОВЛЕНИЕ CONTEXT.md:
[раздел 2] Состояние: <что поменялось>
[раздел 6] TODO: <что закрыто / добавлено>
[раздел 8] Журнал: <новая запись>
```

Просто копируй в соответствующие места.