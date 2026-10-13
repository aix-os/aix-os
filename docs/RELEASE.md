# 🚀 AIX OS — Release Guide

Пошаговая инструкция выхода в мир. Порядок важен.

---

## 1. Проверить готовность (5 минут)

```powershell
# Ноды живы
Invoke-RestMethod http://127.0.0.1:8010/status | Select-Object height, total_supply_aix

# Brain работает
.venv\Scripts\python.exe cli\main.py brain health
# Ожидаемо: Backend OK, Model qwen2.5:3b, 19 tools

# Тесты зелёные
.venv\Scripts\python.exe -m pytest tests\ -q
# Ожидаемо: 77 passed

# Промо-ролик существует
Get-Item docs\promo.mp4 -ErrorAction SilentlyContinue
```

Если чего-то нет:

```powershell
# Сгенерировать промо
.venv\Scripts\python.exe scripts\make_promo.py

# Сгенерировать иконки
.venv\Scripts\python.exe scripts\make_icons.py
```

---

## 2. Git push на GitHub

### 2.1. Проверить репо

Открой в браузере: **https://github.com/aix-os**

- Если это **твой** аккаунт или организация → идём дальше
- Если чужой → создай свой и запомни логин

### 2.2. Заменить URL, если логин не `kikini-bot`

```powershell
# Замени kikini-bot на свой github-username
.venv\Scripts\python.exe scripts\patch_github_url.py kikini-bot
```

Проверь — в `web/landing/index.html`, `web/landing/roadmap.html`, `README.md` больше нет `kikini-bot`.

### 2.3. Коммит и push

```powershell
git status
git add .
git commit -m "feat: AIX Brain (19 tools) + landing v2 + roadmap + icons + promo renderer"
git remote -v
# Если remote не `github.com/aix-os/aix-os.git`:
git remote set-url origin https://github.com/aix-os/aix-os.git
git push -u origin main
```

Если репо нет:

1. https://github.com/new → Name: `AIX-OS` → Public → **НЕ инициализируй README** → Create
2. `git remote add origin https://github.com/<kikini-bot>/AIX-OS.git`
3. `git branch -M main`
4. `git push -u origin main`

### 2.4. Проверить

Открой `https://github.com/aix-os/aix-os`. README должен отрендериться красиво (заголовок ⚡ AIX OS, ASCII-схема, badge).

---

## 3. Habr

### 3.1. Подготовка

```powershell
# Проверь, что в статье нет placeholder-ов
Select-String -Path docs\HABR_ARTICLE.md -Pattern "kikini-bot|kikini-bot" | Select-Object LineNumber, Line
```

Если есть `kikini-bot` — открой `docs/HABR_ARTICLE.md` и замени на свой логин.

### 3.2. Публикация

1. Открой **https://habr.com/ru/sandbox/write/**
2. Заголовок: **AIX OS: как я построил операционную систему, которая слышит тебя**
3. Тело: **целиком** скопируй `docs/HABR_ARTICLE.md`
4. Хабы:
   - Разработка → Программирование
   - Разработка → Искусственный интеллект
   - Разработка → Блокчейн
5. Теги: `python`, `блокчейн`, `ai`, `llm`, `open source`, `ollama`, `децентрализация`
6. **Опубликовать в sandbox**

### 3.3. После публикации

- Первые 2 часа — **активно отвечай в комментариях**
- Хабр уважает тех, кто не сбегает
- Модерация 1–3 дня, потом перенос в основную ленту

---

## 4. VK / Telegram

Текст поста: `docs/POST_VK_TELEGRAM.md` (готов целиком).

Прикрепи **`docs/promo.mp4`** (сгенерированный).

**Куда:**
- **VK:** твой профиль + тематические группы (крипто, AI, open source)
- **Telegram:** свой канал + `@ru_python` (если правила канала позволяют)

---

## 5. Reddit / HN (английский, через 3-7 дней)

Тексты: `docs/POST_HN_REDDIT.md` (готовы целиком).

**Порядок:**
1. Hacker News — **Show HN: AIX OS — decentralized OS with local LLM tool-calling**
2. Через 2 дня — `r/LocalLLaMA`
3. Через неделю — `r/cryptocurrency`

Не публикуй всё в один день. Сначала смотри реакцию, потом масштабируй.

---

## 6. Через неделю — что делать

- Смотреть issues на GitHub → отвечать в течение 24 часов
- Смотреть звёзды → если > 50 за неделю, хорошо
- Смотреть комментарии на Habr → фиксить найденные баги в отдельные коммиты
- **Не менять** основные решения проекта (см. `CONTEXT.md` §4) под давлением комментариев

---

## 7. Если что-то ломается

### Git push падает с ошибкой авторизации

```powershell
# Проверь, что Git настроен на твой аккаунт
git config --global user.name
git config --global user.email
```

Если пусто — задай:
```powershell
git config --global user.name "Твоё имя"
git config --global user.email "твой@email"
```

Для HTTPS push нужен Personal Access Token (не пароль):
https://github.com/settings/tokens → Generate new token (classic) → scopes: `repo`, `workflow` → скопируй → используй как пароль при `git push`.

### Habr отклонил статью

- Модераторы часто просят убрать явную рекламу токена → убери упоминания «21 000 000 AIX» если попросят
- Или добавь в конце дисклеймер «проект не является ICO, токен не продаётся»
- **Не удаляй статью** — жди ответа модераторов, вежливо уточни причину

### Комментарии жёсткие

- Это нормально. Хабр — не ютуб.
- Отвечай технически, не эмоционально
- Если комментатор прав — скажи «спасибо, фикшу» и открой issue
- Если не прав — спокойно объясни

---

## 8. Что НЕ делать

❌ Не публиковать всё в один день  
❌ Не отвечать на критику грубо  
❌ Не обещать фичи, которых нет  
❌ Не менять core-решения проекта под давлением  
❌ Не игнорировать issues  

---

**Империя начинается с тебя.**