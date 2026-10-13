# 🎬 Как записать демо AIX Brain (5 минут)

Цель: **GIF 10–15 секунд**, где видно:
1. Терминал с Brain.
2. Вопрос на естественном языке.
3. Модель думает и вызывает tool.
4. Ответ.

Такой GIF работает везде: Habr, VK, Telegram, GitHub README.

---

## 1. Подготовка

### 1.1. Прогрей модель

Первый запрос — самый долгий (модель грузится в RAM). Прогрей, чтобы запись была быстрой:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/generate -Method Post `
  -ContentType "application/json" `
  -Body '{"model":"qwen2.5:3b","prompt":"привет","stream":false}'
```

### 1.2. Запусти ноды

```powershell
.\scripts\run_all.ps1
```

### 1.3. Убедись, что Brain жив

```powershell
.venv\Scripts\python.exe cli\main.py brain health
```

Ожидаемо: `Backend: OK`, `Model: qwen2.5:3b`, `Installed: True`.

---

## 2. Настрой окно терминала

- Размер: **~110 символов в ширину**, **~30 строк**.
- Шрифт: **Consolas 14pt** или **JetBrains Mono 14pt**.
- Тёмная тема (у AIX OS всё в теме по умолчанию).
- Скрой всё лишнее: закрой вкладки браузера, мессенджеры, уведомления.

---

## 3. Сценарий (рекомендую A)

### Сценарий A — «Я говорю, ОС действует»

```
1. Запуск: brain chat --wallet alice
2. Пишешь: какая высота цепочки?
3. Ждёшь ответ (10–20 сек)
4. Пишешь: отправь 1 AIX bob
5. Видишь preview, жмёшь y
6. Видишь TX ID
7. Выходишь: exit
```

### Сценарий B — «Три вопроса, три tool-call'а»

```
1. brain chat --wallet alice
2. > сколько сейчас блоков?            [chain_status]
3. > покажи мою репутацию              [wallet_balance]
4. > что ты помнишь о проекте?         [ai_memory_brief]
```

---

## 4. Запись

### Windows: ShareX (бесплатно, лучший вариант)

1. Скачай: https://getsharex.com
2. **Capture → Screen recording (GIF)**.
3. Выбери область — только окно терминала.
4. **FPS: 10**.
5. Старт (Ctrl+Shift+PrintScreen).
6. Прогони сценарий (30 сек).
7. Стоп. Сохранится GIF ~1–3 MB.

### Альтернатива: OBS Studio

- https://obsproject.com — запись MP4.
- После — конвертировать в GIF через ffmpeg.

### Linux/Mac

- **peek** (Linux) — идеален для GIF терминала.
- **Kap** (Mac) — то же.
- **asciinema** + **agg** — самый чистый результат, но сложнее.

---

## 5. Обработка

### MP4 → GIF через ffmpeg

```bash
ffmpeg -i demo.mp4 -vf "fps=12,scale=1000:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 demo.gif
```

Онлайн-альтернатива: https://ezgif.com/video-to-gif

### Проверь размер

- **< 3 MB** — идеально.
- **3–5 MB** — терпимо.
- **> 5 MB** — уменьши FPS до 8, ширину до 800 px.

---

## 6. Куда сохранить

```
docs/
├── demo.gif              ← главный GIF
├── demo-preview.png      ← первый кадр как PNG
└── DEMO_RECORDING.md     ← этот файл
```

В `README.md` сверху добавить:

```markdown
![AIX OS demo](docs/demo.gif)
```

---

## 7. Хэштеги

**Habr:** `#блокчейн` `#ai` `#llm` `#open_source` `#python` `#ollama` `#криптовалюты` `#децентрализация`

**Telegram:**
> 🧠⚡ AIX OS — операционная система, которая слышит тебя
> Скажи «отправь 5 AIX маме» — она сделает. Ключ LLM не видит.
> #AIXOS #AI #Blockchain #OpenSource

**VK:** то же + GIF + ссылки на Habr и GitHub.

---

## 8. Чеклист перед записью

- [ ] Модель прогрета
- [ ] Ноды запущены
- [ ] `brain health` показывает OK
- [ ] Терминал настроен
- [ ] Уведомления выключены
- [ ] Никаких приватных ключей на экране
- [ ] GIF < 3 MB
- [ ] Первый кадр сохранён как preview.png

**Итого: 5 минут. Один GIF — лицо проекта на ближайшие месяцы.**