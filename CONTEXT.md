# 🧠 AIX OS — CONTEXT для AI-ассистента

> **В начале новой AI-сессии скинь этот файл ЦЕЛИКОМ + вывод `python scripts/ai_brief.py`.**

---

## 1. Что за проект

**AIX OS** — децентрализованная операционная система для жизни.
Свой блокчейн (PoW, ECDSA secp256k1, Base58Check-адреса `AIX...`).
Тикер: **AIX**. Максимум: 21 000 000. Pre-mine: 0%.

Кредо: *«Технологии должны делать людей счастливее, а не богаче.»*
Слоган: *«Империя начинается с тебя.»*

**Стек:**
- Python 3.11+ + FastAPI + Uvicorn + ECDSA + base58
- Web Wallet — чистый HTML/JS + Chart.js
- CLI — argparse + colorama + tabulate
- **AIX Brain** — Ollama (qwen2.5:3b) + tool-calling
- Мобильное — Flutter (собрано под Windows)

---

## 2. Текущее состояние

- **Высота цепочки:** 17
- **Ноды:** A (8010), B (8011)
- **Кошельки:** alice, bob, carol, miner, dave
- **AIX-ID:** @alice, @bob, @carol, @miner, @dave
- **Майнер:** `AIXTYTXqm8WBFE6iX9UCFsp3qbF3VoKjAMxG8`
- **Основатель:** `alice` (`AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2`)
- **Brain модель:** `qwen2.5:3b` (влезает в 7 GB RAM)
- **Brain tools:** 19
- **Тесты:** 77 passed
- **Web UI:** обзор, кошельки, отправка, swap, PoC, медали, контакты, артефакты, AI Memory, DAO, **Brain**
- **Публикация:** готово к git push + Habr + VK/Telegram

---

## 3. Карта файлов (ключевое)

### 🔴 Ядро
- `config.py`, `core/block.py`, `core/chain.py`, `core/transaction.py`,
  `core/mempool.py`, `core/wallet.py`, `storage/db.py`

### 🟡 Протоколы (`core/protocols/`)
`gift_link.py`, `time_lock.py`, `sbt.py`, `lottery.py`, `dead_mans_switch.py`,
`aix_id.py`, `burn_to_mint.py`, `contacts.py`, `swap.py`, `poc.py`,
`state_sync.py`, `ai_memory.py`

### 🏛 Governance
- `core/governance/dao.py`

### 🧠 AIX Brain (`ai/brain/`)
- `config.py` — BrainConfig, env `AIX_BRAIN_*`
- `client.py` — HTTP к Ollama
- `tools.py` — 19 инструментов + JSON-схемы
- `memory_bridge.py` — мост в AI Memory
- `signer.py` — BaseSigner / NullSigner / CLISigner
- `agent.py` — оркестратор LLM ↔ tools

### 🌐 Сеть
- `network/server.py` — FastAPI + P2P + `/brain/*`
- `network/peer.py`, `network/peer_manager.py`

### 💻 Интерфейсы
- `cli/main.py` — CLI (`brain chat --wallet`)
- `web/index.html` — Web Wallet (вкладки + Brain + AI Memory + DAO)
- `web/landing/index.html` — лендинг v2
- `web/landing/roadmap.html` — roadmap
- `web/landing/favicon.svg` + `.ico` + иконки PWA + manifest
- `integrations/telegram/bot.py`
- `mobile/flutter_app/lib/`

### 🛠 Скрипты (`scripts/`)
- `run_all.ps1`, `stop_all.ps1`
- `patch_brain*.py` (6 патчей), `patch_web_icons.py`
- `make_icons.py`, `make_promo.py`, `install_promo.ps1`
- `debug_brain_tools.py`
- `ai_remember.py`, `ai_brief.py`, `dump_for_ai.py`
- `patch_github_url.py` — замена URL GitHub в web-файлах

### 📜 Документы
- `README.md` (EN) — публичное лицо для GitHub
- `CONTEXT.md` (этот файл)
- `docs/WHITEPAPER.md`
- `docs/HABR_ARTICLE.md`
- `docs/DEMO_RECORDING.md`
- `docs/RELEASE.md` — пошаговая инструкция публикации
- `docs/POST_VK_TELEGRAM.md` — готовый пост
- `docs/POST_HN_REDDIT.md` — англоязычные посты

### 🧪 Тесты
- `tests/test_ai_memory.py` (11)
- `tests/test_brain.py` (22)
- `tests/test_brain_signer.py` (14)
- `tests/test_brain_tools_write.py` (19)
- `tests/test_dao.py` (11)

---

## 4. Ключевые решения (не менять!)

| Что | Значение |
|-----|----------|
| Кривая | ECDSA secp256k1 |
| Адрес | `AIX` + Base58Check(0x41 + hash160) |
| Хеш | Двойной SHA-256 |
| Награда | 50 AIX, халвинг 210k |
| Pre-mine | 0% |
| Phone salt | `AIX-OS-PHONE-v1` |
| AMM | x*y=k, fee 0.3%, min 5% |
| PoC уровни | MICRO≤100(1), SMALL≤1000(2), MEDIUM≤5000(3), LARGE(5) |
| DAO | QUORUM=30%, PASS>50%, VOTING=100, DELAY=20 |
| Brain default model | `qwen2.5:3b` |
| Brain timeout | 300 сек |
| Brain write-безопасность | CLI y/N через CLISigner, HTTP — NullSigner |

---

## 5. Правила работы (грабли)

1. **PowerShell 5.1 не читает UTF-8 без BOM** — все `.ps1` на ASCII.
2. **`curl` в PowerShell — это Invoke-WebRequest**, глючит. Используй `Invoke-RestMethod`.
3. **FastAPI без `--reload` не подхватывает патчи** — перезапускай ноды.
4. **venv активируется не всегда** — `.venv\Scripts\python.exe ...` явно.
5. **Патчи больших файлов — только скриптом**. HTML — только ПОЛНОЙ ЗАМЕНОЙ.
6. **Windows IPv6 `localhost`** — везде `127.0.0.1`.
7. **Ollama на Windows:** GUI в трее ≠ сервер. Проверяй `netstat -ano | Select-String ":11434"`.
8. **RAM < 8 GB** — модель не больше 3B.
9. **Env `AIX_BRAIN_MODEL`** перебивает дефолт. `Remove-Item Env:AIX_BRAIN_MODEL`.
10. **Favicon кэшируется** — после правки `Ctrl+F5` или приватное окно.
11. **Новый чат = `CONTEXT.md` + `AI_BRIEF.md` в первом сообщении.**

---

## 6. TODO

- [x] ✅ `ai/brain/` — локальная LLM (Ollama)
- [x] ✅ Brain Send / Gift / TimeLock / Swap / SBT / AIX-ID
- [x] ✅ Web UI вкладка Brain (read-only)
- [x] ✅ Лендинг v2 + roadmap + иконки
- [x] ✅ README EN + Habr + Demo guide
- [x] ✅ Промо-рендерер
- [ ] 🎯 **git push origin main** (public GitHub)
- [ ] 🎯 **Habr sandbox**
- [ ] 🎯 **VK/Telegram**
- [ ] 🎬 Сгенерировать промо-ролик (`make_promo.py`)
- [ ] 📱 Flutter → Android APK
- [ ] 🎙️ Voice: Whisper + Piper
- [ ] 🔐 `crypto/zk/`
- [ ] 📡 `network/mesh/lora.py`
- [ ] 🧹 Чистка репо

---

## 7. Как запускать

```powershell
.venv\Scripts\Activate.ps1
.\scripts\run_all.ps1
.\scripts\stop_all.ps1

# Brain
python cli/main.py brain health
python cli/main.py brain chat --wallet alice

# Промо
.venv\Scripts\python.exe scripts\make_promo.py
.venv\Scripts\python.exe scripts\make_icons.py

# AI Memory
python cli/main.py ai remember "текст" --kind=MILESTONE --priority=CRITICAL
python cli/main.py ai brief -o AI_BRIEF.md
```

**Порты:** A=8010, B=8011, Web=9000, Ollama=11434

---

## 8. Журнал сессий

### 2026-10-13 (сессия 4) — Brain + Выход в мир
- Слой `ai/brain/` (config, client, tools, memory_bridge, signer, agent)
- 19 инструментов
- CLI: `brain health | ask | chat --wallet | send | remember`
- API: `/brain/health`, `/brain/ask`
- Безопасность: NullSigner (HTTP) vs CLISigner (CLI, y/N)
- Web UI: вкладка 🧠 Brain (read-only)
- Лендинг v2 + roadmap.html + иконки + manifest
- README EN + Habr-статья + demo guide + release guide
- Промо-рендерер (30 сек, 7 сцен)
- 77 тестов passed

### 2026-10-12 (сессия 3)
- AI Memory (#AI-1)
- DAO (#13)
- Cross-node sync
- IPv6 fix

### 2026-10-11 (сессия 2)
Загрузка проекта, первый обзор.

---

## 9. Правила работы с AI

1. В начале — `CONTEXT.md` + `AI_BRIEF.md`.
2. В конце — обновить файл + `ai remember` (SESSION_END).
3. Не показывать `*.wallet.json`.
4. Патчи в `core/` и `crypto/` — предупреждать.
5. **Формат ответа AI — ЦЕЛЫЕ ФАЙЛЫ или ПАТЧ-СКРИПТЫ, не куски.**