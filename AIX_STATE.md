# AIX OS — Состояние проекта (Context Dump)

**Дата:** 2026-10-29 (последняя сессия)
**Версия:** v0.1.0-alpha
**Block height:** 85283+
**Total supply AIX:** 7 099 200+ (плюс 2.1B vesting pre-mine)
**Виртуальные данные:** 41+ кошелёк, 10 AIX-ID, 4 пула, 7 PoC

## ✅ Что сделано и работает

### Блокчейн (Python, порт 8010/8011)
- Собственный блокчейн SHA-256 PoW (не форк, не EVM)
- secp256k1 + base58check адреса (AIXT...)
- WAL-лог + JSON snapshot, mDNS + P2P sync
- Pre-mine: 2 100 000 000 AIX на AIX-DEV (Foundation Reserve, 10% от 21B)

### Мобилка (Flutter, 78-79 MB APK)
- Кошелёк с BIP39 (12 слов) + импорт по hex
- 17 нативных монет (secp256k1): BTC, ETH, BNB, MATIC, USDT, USDC, SHIB, PEPE, LINK, UNI, DAI, LTC, DOGE, XRP, TRX + AIX + aCOIN
- SOL/TON убраны из списка (Ed25519 — другая кривая)
- Реальная отправка: BTC (BlockCypher UTXO), ETH/BNB/MATIC (RLP+secp256k1), USDT/USDC/SHIB/PEPE (ERC-20 data payload), AIX (подпись payload), aCOIN (swap-модуль)
- aCOIN (wrapped токены) + автосоздание пулов через token_register
- aCOIN Manager v2: контракт, эмиссия, создатель, ликвидность, LP, обмен
- AIX-ID @имена: регистрация при создании/импорте кошелька + экран /register-id
- Резолв @name → адрес в UniversalSendScreen
- WebSocket мессенджер (нативный AIX + Telegram TDLib)
- Мега-Императорский мессенджер v2 (неоновый, аватары AIX-ID, online, typing)
- Telegram-клиент через TDLib (в разработке, есть блокер)
- DEX (AMM x*y=k, fee 0.3%): AIX/BTC, AIX/DOGE, AIX/ZRZ, AIX/ETH
- Swap-история (отдельный экран)
- PoC, DAO, SBT, Burn, Timelock, DMS, Gifts (escrow через клиентскую подпись)
- AIX Brain (локальный AI-наставник)
- Faucet (1 AIX, IP-rate-limit, миграция old 'ts' → 'time')
- Vesting-контракт on-chain: 4 года linear, проверка в Transaction.is_valid
- Публичные endpoints: /public/stats, /public/health, /public/markets, /public/vesting
- Whitepaper: http://localhost:9000/whitepaper/
- QR-сканер, PIN, сообщение (только AIX)

## 🔧 Критичные фиксы (все применены)

### 1. Decimals (10^8 vs 10^18) — ГЛАВНЫЙ БАГ
- Было: /swap/quote и /swap/execute умножали amount на config.SATOSHI (10^8), пул в 10^18 → рассинхрон 10^10
- Фикс: `int(req.amount_in_aix * 10**18)` в swap_quote и swap_execute
- Аналогично reserve_a/b, total_lp в /swap/pools: /10^18, не /SATOSHI

### 2. Sign_transaction / is_valid — подпись
- Было: `sign_transaction` писал signature как bytes, `is_valid` ждал hex → TypeError
- Фикс: `self.signature = signature.hex() if isinstance(signature, bytes) else signature`

### 3. Gift-Link escrow
- Было: gift создавался, но не списывал sender; claim падал с "нельзя подписать"
- Фикс: /gift/create-signed принимает подпись клиента → escrow в GIFT-ESCROW, claim через GIFT-ESCROW → recipient (системный sender, без подписи)

### 4. Vesting pre-mine (дубль 4.2B)
- Было: ensure_premine() при перезапуске создавал 2 tx (баланс 4.2B вместо 2.1B)
- Фикс: проверка mempool на дубли (tx.sender == COINBASE, tx.recipient == addr)
- Фикс: бэкап и восстановление транзакции (блок #85283 откачен, pre-mine перезапущен, баланс ровно 2.1B)
- РАБОТАЕТ ON-CHAIN: 600M AIX отклоняет с "vesting: разблокировано 477M", 100M проходит

### 5. Faucet (null / 10 AIX)
- Было: FAUCET_AMOUNT_AIX был 10 в коде, но кэшировался null
- Фикс: сервер возвращает status:error при исключении; миграция faucet_8010.json (ts→time); клиент обрабатывает error

### 6. resolve_who (fallback на Wallet)
- Было: resolve_who("@aix") → возвращал "aix", не адрес
- Фикс: fallback id_manager → Wallet.load(name).address

### 7. aCOIN конфликты
- Было: aCOIN ETH не добавлялся, т.к. символ совпадал с native
- Фикс: chain == 'AIX (aCOIN)' с badge 'wrapped', нативный ETH остаётся отдельно

### 8. Skip-list в _updateBalances
- Было: BTC/ETH/USDT aCOIN не попадали в список
- Фикс: убрали skip-list, кроме 'AIX'

### 9. Sign_transaction (Python) — крипто
- Уже выше, фикс signature → hex

### 10. Force mine_block заменён на mempool
- Было: ensure_premine звал blockchain.mine_block (не существует)
- Фикс: pre-mine tx в mempool, следующий /mine закрывает

### 11. UniversalSendScreen TDLib/payload
- Было: 404 (endpoint /sync/tx вместо /tx/submit)
- Фикс: /sync/tx → /tx/submit
- Плюс 500 (AttributeError private_key) — убран из swap_execute

### 12. Mobile storage hang (old)
- encryptedSharedPreferences: false, timeout 8s, allowBackup=false, minSdk=23
- НЕ забывать при flutter clean (сбрасывается в build.gradle.kts)

## ⚠️ Блокеры и незакрытые задачи

### Блокер TDLib (сейчас)
- Пакет `tdlib2: ^1.8.64` на pub.dev (только 1 версия)
- Релиз kingwill101/tdlib@v1.8.64 полностью сломан: ВСЕ архивы (arm, arm64, x64, x86) содержат x86_64 `.so`
- Релиз v1.8.65 ПОЧИНЕН: arm64 архив = 8.9 MB, содержит правильный aarch64 (проверено)
- Скачан `tdlib-arm64-v1.8.65.tar.gz` (9.4 MB) в `mobile/flutter_app/`
- Внутри: `libtdjson.so` 19.4 MB, ELF machine 0xB7 (aarch64) ✅
- Проблема: `flutter clean` снёс `.dart_tool` с заменёнными бинарниками
- НЕ ЗАПУСКАТЬ `flutter clean` пока не починим tdlib2!

### Фикс TDLib (следующий шаг)
1. Найти в `tdlib2-1.8.64/lib/src/android_builder.dart` URL v1.8.64 → заменить на v1.8.65
2. Либо использовать UserDefinePrebuiltResolver (env-переменная, штатный механизм)
3. Либо вручную распаковать v1.8.65.tar.gz в `.dart_tool/hooks_runner/shared/tdlib2/build/*/libtdjson.so` после `flutter pub get`, но ДО сборки

### Lock-файл tdlib2 (актуально)
- `flutter clean` не убивает lock: `.dart_tool/hooks_runner/shared/tdlib2/.lock`
- При сборке 5 минут ждёт lock, потом фейл
- Фикс: убить java/dart процессы + удалить lock + пересобрать
- Без clean — tdlib2 использует кэш, сборка 2-3 минуты

### Открытые задачи
- Гибридный консенсус PoW+BFT (Q3 2026)
- ML-DSA (Dilithium) постквантовые подписи (Q4 2026)
- Листинг на GeckoTerminal/DexScreener (автоиндексация по ликвидности)
- CoinGecko / CMC submission
- Малые CEX: LBank, XT, Bitget
- Фиатный шлюз (Яндекс/ЮMoney)
- Реакции в чате, копирование сообщений
- Медиа в чате (фото через ImagePicker)
- SOL/TON (отдельная Ed25519 сид-фраза)

## 📚 Грабли (важно запомнить)

### Windows + PowerShell
- Here-string `@'...'@` ОБЯЗАТЕЛЬНО с новой строки после `@'` и перед `'@`
- `Out-File -Encoding utf8` сохраняет с BOM — Python это переживает, но иногда нужен `-Encoding utf8NoBOM`
- `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` перед каждым новым окном
- `cd` в PS не сохраняется между окнами — проверять `pwd` перед запуском скриптов

### Python-скрипты патча
- ВСЕГДА `shutil.copy(p, p.with_suffix(".py.bak_N"))` перед правкой
- ВСЕГДА пробовать `import module; print('OK')` после патча — если падает, откатить
- Regex-патчи опасны: `(?:        [^
]+
)+` может сожрать следующий метод
- Лучше точная замена одной строки, чем regex-блок
- Для многострочных блоков — anchor по `def \w+\(`, не по отступу

### Git + Python
- `git status` не видит `network/server.py` (assume-unchanged или другой индекс)
- `git restore lib/` может снести локальные правки (lib/ не в git отслеживается)
- `data/` содержит приватные ключи — `.gitignore` обязателен для `aix_dev_key.json`

### Flutter
- `flutter clean` сбрасывает ВСЁ: `.dart_tool`, `build/`, локальный `build.gradle.kts` (minSdk!)
- `pubspec.lock` — версии закрепляются, `^` может тянуть несовместимое
- `--target-platform=android-arm64` ОБЯЗАТЕЛЕН, иначе tdlib2 тянет x86_64 для эмулятора
- `--split-per-abi` создаёт 3 APK, но tdlib2 всё равно требует все ABI (если не abiFilters)
- `--no-tree-shake-icons` — обязателен, иначе emoji ломают сборку

### Сервер (FastAPI + uvicorn)
- Traceback только в консоли сервера, HTTP ответ — "Internal Server Error"
- `/public/*` — публичные endpoints (для бирж), не требуют подписи
- `blockchain.ensure_premine()` вызывается при `_create_genesis` и при старте (после load)
- `vesting.init(blockchain)` ОБЯЗАТЕЛЬНО до `ensure_premine`

## 🎯 Минимальный план на следующую сессию

### Приоритет 1: TDLib arm64 (30 минут)
1. `Get-Content tdlib-arm64-v1.8.65.tar.gz` — проверить, что файл на месте
2. Распаковать в `mobile/flutter_app/tdlib-arm64-v1.8.65/` (уже распаковано)
3. Найти `android_builder.dart` и `tdlib_source.dart` — что качает и откуда
4. Найти env-переменную для UserDefinePrebuiltResolver (в логе был "Trying UserDefinePrebuiltResolver...")
5. Если есть env → подставить путь к распакованному arm64 → сборка пройдёт
6. Если нет → правка URL v1.8.64 → v1.8.65 в `.dart` файле пакета tdlib2 (в pub-cache)
7. Пересборка БЕЗ clean

### Приоритет 2: Реакции + копирование в чате (10 минут)
- `_showMenu` в chat_v2_screen: Copy → `Clipboard.setData`, реакции → `/messages/react`

### Приоритет 3: Vesting в мобилке
- Импорт AIX-DEV (ключ в `data/aix_dev_key.json`) → проверка, что 600M отклоняется

### Приоритет 4: Друзья и майнинг
- Друзья майнят на своих нодах — pre-mine их не касается
- Если fork — replace_chain через /sync/pull

## 🔐 Приватные ключи (НЕ в git!)
- `data/aix_dev_key.json` — AIX-DEV (2.1B AIX vesting), в .gitignore
- Адрес AIX-DEV: `AIXTLqpgpWrtKQiBD1gAJQxLm36y9jQUJWh6E`
- Vesting start: 1764547200 (1 декабря 2025, UTC)
- Vesting duration: 4 * 365 * 86400 = 126 144 000 сек
