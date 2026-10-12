# 🧠 AIX OS — CONTEXT для AI-ассистента

> **Как пользоваться:** в начале новой AI-сессии скинь этот файл целиком
> ПЛЮС вывод `python scripts/ai_brief.py` (это даст AI ещё и память).

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
- **Ноды:** A (8010, `chain_A.json`), B (8011, `chain_B.json`)
- **Mempool:** 0 на обеих нодах ✅
- **PoC:** total_donated=150, total_paid=150 на обеих нодах ✅
- **Chain OK:** ✅
- **Майнер:** `AIXTYTXqm8WBFE6iX9UCFsp3qbF3VoKjAMxG8`
- **Основатель:** `alice` (`AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2`)
- **Наследники:** `bob` (60%) + `carol` (40%) — DMS сработал
- **Swap:** 1 пул (AIX-SIM/USDT-SIM, 1000/500, LP=707.1)
- **SBT:** 2 медали (FOUNDER у alice, EARLY_BIRD у bob)
- **Burn:** 1 артефакт (COM-001, Уголёк #1)
- **Contacts:** 1 хеш номера у alice
- **Последний коммит:** `e9f91fd`
- **origin/main:** `e9f91fd`

---

## 3. Карта файлов

### 🔴 Ядро
- `config.py` — все константы
- `core/block.py`, `core/chain.py`, `core/transaction.py`,
  `core/mempool.py`, `core/wallet.py`
- `storage/db.py` — ChainStorage

### 🟡 Протоколы (`core/protocols/`)
- `gift_link.py`, `time_lock.py`, `sbt.py`, `lottery.py`,
  `dead_mans_switch.py`, `aix_id.py`, `burn_to_mint.py`,
  `contacts.py`, `swap.py`, `poc.py`, `state_sync.py`
- 🆕 **`ai_memory.py`** — AI Memory (#AI-1)

### 🌐 Сеть
- `network/server.py` (~1761 строк)
- `network/peer.py`, `network/peer_manager.py`

### 💻 Интерфейсы
- `cli/main.py` (~2072 строки)
- `web/index.html` (~833 строки)
- `integrations/telegram/bot.py`
- `mobile/flutter_app/lib/` — 7 экранов

### 📜 Документы
- `README.md`, `ROADMAP.md`, `docs/WHITEPAPER.md`
- `docs/index.html` + `web/landing/index.html` — лендинг (дубли)

### 🛠️ Скрипты (`scripts/`)
- `run_all.ps1`, `stop_all.ps1`, `backup.ps1`, `mine_batch.ps1`
- `faucet.py`, `init_genesis.py`, `reset_db.py`, `debug_lottery.py`
- `fix_data.py` — одноразовый фикс
- `dump_for_ai.py` — дамп всего проекта
- 🆕 **`ai_remember.py`** — записать воспоминание
- 🆕 **`ai_brief.py`** — собрать бриф для AI

---

## 4. Ключевые решения (не менять!)

| Что | Значение |
|-----|----------|
| Кривая | ECDSA secp256k1 |
| Адрес | `AIX` + Base58Check(0x41 + hash160) |
| Хеш | Двойной SHA-256 |
| Награда | 50 AIX, халвинг 210k |
| Майнер | `COINBASE` (системный) |
| Сжигание | `recipient="BURN"` |
| PoC фонд | `POC-POOL` (системный) |
| Phone salt | `AIX-OS-PHONE-v1` (не менять!) |
| AMM | x*y=k, fee 0.3%, min 5% |
| PoC уровни | MICRO≤100(1), SMALL≤1000(2), MEDIUM≤5000(3), LARGE(5) |

---

## 5. ✅ Закрытые баги

### Баг #1 — Stale-tx в mempool (закрыт)
`chain.py::replace_chain()` чистит mempool от включённых tx.

### Баг #2 — Рассинхрон PoC-пула (закрыт)
`poc.py::import_pool()` merge по ключам.

### Баг #3 — Незавершённый rebase (закрыт)
`git rebase --abort` + `git reset --hard origin/main`.

---

## 6. TODO

- [ ] Наполнить `core/governance/dao.py` — PoC → DAO с голосованием
- [ ] Наполнить `ai/brain/` — локальная LLM (Ollama)
- [ ] Наполнить `crypto/zk/` — ZK-proofs
- [ ] Наполнить `network/mesh/lora.py` — оффлайн-сеть
- [ ] Написать тесты в `tests/`
- [ ] Почистить репо: `data_backup_*`, `web_backup/`, `*.backup`
- [ ] Обновить статистику на лендинге
- [ ] Исправить commit `b736970`
- [ ] Довести Flutter до Android APK
- [ ] Добавить AI Memory в API (`network/server.py`)
- [ ] Добавить AI Memory в CLI (`cli/main.py`)
- [ ] Добавить AI Memory в Web Wallet

---

## 7. Как запускать

```powershell
.venv\Scripts\Activate.ps1
.\scripts\run_all.ps1          # 2 ноды + web
.\scripts\stop_all.ps1         # остановить
python scripts/fix_data.py     # фикс данных
python cli/main.py node status # статус ноды

# 🆕 AI Memory:
python scripts/ai_remember.py "Заголовок" --kind=MILESTONE --priority=IMPORTANT
python scripts/ai_brief.py > AI_BRIEF.md
```

**Порты:** A=8010, B=8011, Web=9000, Swagger=`http://localhost:8010/docs`

---

## 8. Журнал сессий

### 2026-10-12 (сессия 3)
- Полный dump проекта (217 файлов, 23 632 строки)
- Патч `chain.py::replace_chain()` — mempool cleanup
- Патч `poc.py::import_pool()` — merge по ключам
- Патч `storage/db.py::load()` — автоочистка stale-tx
- Создан `scripts/fix_data.py`, `scripts/dump_for_ai.py`, `CONTEXT.md`
- `fix_data.py` отработал: удалено 1 stale-tx из `chain_B.json`
- Оба бага закрыты
- Коммиты: `0000948` (fix) + `e9f91fd` (chore)
- 🆕 **Создан AIX Memory** — память AI на блокчейне
  - `core/protocols/ai_memory.py`
  - `scripts/ai_remember.py`
  - `scripts/ai_brief.py`

### 2026-10-11 (сессия 2)
Загрузка проекта, первый обзор.

---

## 9. Правила работы с AI

1. В начале сессии — скинуть `CONTEXT.md` + `AI_BRIEF.md`
2. В конце сессии — обновить разделы 2, 6, 8 + записать воспоминание:
   ```powershell
   python scripts/ai_remember.py "Что сделали" --kind=MILESTONE --priority=IMPORTANT
   ```
3. Не показывать AI файлы `*.wallet.json`
4. Патчи в `core/` и `crypto/` — предупреждать явно
5. Формат ответа AI — целые файлы или точные пути

---

## 10. Как обновлять этот файл

AI в конце сессии даёт блок:

```
📝 ОБНОВЛЕНИЕ CONTEXT.md:
[раздел 2] Состояние: <что поменялось>
[раздел 6] TODO: <что закрыто / добавлено>
[раздел 8] Журнал: <новая запись>
```

Плюс записывает воспоминание:
```powershell
python scripts/ai_remember.py "Итог сессии" --kind=SESSION_END --priority=IMPORTANT
```

И следующая сессия начнётся с `ai_brief.py` — я всё вспомню.