"""
AIX OS — Telegram Bot.

Простой клиент к REST API ноды.
Работает в любом Telegram — не требует установки приложения.

Запуск:
    1. Получи токен у @BotFather в Telegram
    2. Установи переменную: $env:AIX_BOT_TOKEN = "твой_токен"
    3. python -m integrations.telegram.bot

Требования:
    pip install python-telegram-bot requests
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

BOT_TOKEN = os.getenv("AIX_BOT_TOKEN", "")
NODE_URL = os.getenv("AIX_NODE_URL", "http://localhost:8010")

# Хранилище сессий пользователей (в памяти)
# {user_id: {"wallet_address": "AIX...", "wallet_name": "alice"}}
SESSIONS = {}

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =============================================================================
# API-ХЕЛПЕРЫ
# =============================================================================

def api_get(path: str, timeout: float = 5.0):
    try:
        r = requests.get(f"{NODE_URL}{path}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException as e:
        logger.warning(f"API GET {path}: {e}")
    return None


def api_post(path: str, body: dict, timeout: float = 10.0):
    try:
        r = requests.post(f"{NODE_URL}{path}", json=body, timeout=timeout)
        data = r.json()
        if r.status_code == 200:
            return data, None
        return None, data.get("detail", "Ошибка")
    except requests.RequestException as e:
        return None, str(e)


def get_wallet(user_id: int) -> dict:
    """Получить кошелёк пользователя."""
    return SESSIONS.get(user_id, {})


def set_wallet(user_id: int, address: str, name: str):
    SESSIONS[user_id] = {"wallet_address": address, "wallet_name": name}


def check_node() -> bool:
    """Проверка, что нода отвечает."""
    return api_get("/status") is not None


# =============================================================================
# КОМАНДЫ
# =============================================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Приветствие."""
    user = update.effective_user
    text = (
        f"🤖⚡ *Привет, {user.first_name}!*\n\n"
        f"Это *AIX OS* — операционная система для жизни.\n"
        f"Тут ты можешь:\n\n"
        f"👛 `balance` — посмотреть баланс\n"
        f"📤 `send @bob 10` — отправить AIX\n"
        f"🎁 `gift 100` — создать Gift-Link\n"
        f"🧬 `poc` — вклады Proof of Contribution\n"
        f"🏅 `medals` — топ по репутации\n"
        f"💱 `swap` — курсы SIM-токенов\n"
        f"📇 `id @alice` — паспорт творца\n"
        f"🔗 `connect <AIX-адрес>` — привязать кошелёк\n"
        f"❓ `help` — все команды\n\n"
        f"🌐 Web Wallet: {NODE_URL.replace(':8010', ':9000')}"
    )
    if not check_node():
        text += f"\n\n⚠️ *Нода недоступна*. Проверь, что запущена на {NODE_URL}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Помощь."""
    text = (
        "*AIX OS Bot — все команды:*\n\n"
        "*Кошелёк:*\n"
        "• `connect AIX...` — привязать адрес\n"
        "• `balance` — баланс\n"
        "• `send @alice 10 [сообщение]` — отправить AIX\n\n"
        "*Фишки:*\n"
        "• `gift 100` — создать Gift-Link\n"
        "• `id @alice` — профиль AIX-ID\n"
        "• `medals` — топ по репутации\n"
        "• `swap` — курсы токенов\n"
        "• `poc` — статистика PoC\n"
        "• `poc submit <кат> <сумма> <название>` — создать вклад\n\n"
        "*Информация:*\n"
        "• `status` — статус сети\n"
        "• `help` — это сообщение"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Статус сети."""
    s = api_get("/status")
    if not s:
        await update.message.reply_text("❌ Нода не отвечает")
        return
    text = (
        f"🖥️ *Статус AIX OS*\n\n"
        f"📊 Высота: `{s['height']}`\n"
        f"💎 Всего AIX: `{s['total_supply_aix']:.2f}`\n"
        f"🔥 Сожжено: `{s['total_burned_aix']:.2f}`\n"
        f"🌐 Пиров: `{s['peers_count']}`\n"
        f"🪪 AIX-ID: `{s['ids_count']}`\n"
        f"🏅 Медалей: `{s['sbt_count']}`\n"
        f"📇 Контактов: `{s['contacts_count']}`\n"
        f"💱 Пулов: `{s['swap_pools_count']}`\n"
        f"🧬 PoC вкладов: `{s['poc_count']}`\n"
        f"🧬 Фонд PoC: `{s['poc_pool_aix']:.2f} AIX`\n"
        f"✅ Цепочка: `{'OK' if s['chain_valid'] else 'BROKEN'}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_connect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Привязать кошелёк."""
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Использование: `connect AIX...`\n\n"
            "Где взять адрес? Открой Web Wallet → Кошельки → скопируй адрес.",
            parse_mode="Markdown"
        )
        return

    address = args[0].strip()
    # Проверяем адрес через API
    bal = api_get(f"/balance/{address}")
    if not bal:
        await update.message.reply_text(
            "❌ Адрес не найден в сети.\n"
            "Убедись, что он начинается с `AIX` и кошелёк существует.",
            parse_mode="Markdown"
        )
        return

    name = bal.get("name") or address[:16]
    set_wallet(update.effective_user.id, address, name)

    text = (
        f"✅ *Кошелёк привязан!*\n\n"
        f"👤 AIX-ID: `@{bal.get('name', '?')}`\n"
        f"💰 Баланс: `{bal['balance_aix']:.4f} AIX`\n"
        f"🏅 Репутация: `{bal.get('reputation', 0)}`\n\n"
        f"Теперь можешь:\n"
        f"• `balance` — проверить баланс\n"
        f"• `send @bob 10` — отправить AIX"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Баланс."""
    w = get_wallet(update.effective_user.id)
    if not w:
        await update.message.reply_text(
            "❌ Кошелёк не привязан. Используй: `connect AIX...`",
            parse_mode="Markdown"
        )
        return

    bal = api_get(f"/balance/{w['wallet_address']}")
    if not bal:
        await update.message.reply_text("❌ Нода не отвечает")
        return

    text = (
        f"💰 *Баланс*\n\n"
        f"👤 AIX-ID: `@{bal.get('name', '?')}`\n"
        f"📊 Всего: `{bal['balance_aix']:.4f} AIX`\n"
    )
    locked = bal.get("locked_aix", 0)
    if locked:
        text += f"🔒 Заморожено: `{locked:.4f} AIX`\n"
        text += f"✅ Доступно: `{bal['available_aix']:.4f} AIX`\n"
    if bal.get("medals_count"):
        text += f"🏅 Медали: `{bal['medals_count']}` (репутация: `{bal['reputation']}`)\n"
    if bal.get("sim_balances"):
        text += "\n*COIN:*\n"
        for tok, amount in bal["sim_balances"].items():
            if amount > 0:
                text += f"• {tok}: `{amount / 1e18:.2f}`\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Отправить AIX. Без приватного ключа (заглушка для MVP)."""
    await update.message.reply_text(
        "📤 *Отправка AIX*\n\n"
        "⚠️ Через Telegram отправка пока недоступна — нужен приватный ключ.\n\n"
        "Используй один из способов:\n"
        f"• *Web Wallet:* {NODE_URL.replace(':8010', ':9000')}\n"
        "• *CLI:* `python cli/main.py node send alice @bob 10`\n\n"
        "В следующих версиях добавим:\n"
        "• Встроенный кошелёк в боте\n"
        "• QR-коды для отправки\n"
        "• Подпись транзакций на телефоне",
        parse_mode="Markdown"
    )


async def cmd_gift(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Gift-Link — создать ссылку."""
    await update.message.reply_text(
        "🎁 *Gift-Link*\n\n"
        "Создать подарочную ссылку можно через Web Wallet:\n"
        f"{NODE_URL.replace(':8010', ':9000')}\n\n"
        "Или через CLI:\n"
        "`python cli/main.py gift create alice 100`\n\n"
        "В следующих версиях добавлю создание прямо в боте.",
        parse_mode="Markdown"
    )


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """AIX-ID."""
    args = ctx.args
    if not args:
        await update.message.reply_text("Использование: `id @alice`", parse_mode="Markdown")
        return

    name = args[0].lstrip("@")
    d = api_get(f"/id/{name}")
    if not d:
        await update.message.reply_text(f"❌ AIX-ID `@{name}` не найден", parse_mode="Markdown")
        return

    text = (
        f"🪪 *AIX-ID: {d.get('avatar', '👤')} @{d['name']}*\n\n"
        f"📝 Имя: `{d.get('display_name', d['name'])}`\n"
        f"💼 Адрес: `{d['address'][:32]}...`\n"
    )
    if d.get("bio"):
        text += f"📖 О себе: _{d['bio']}_\n"
    text += (
        f"\n💰 Баланс: `{d['balance_aix']:.4f} AIX`\n"
        f"🏅 Медали: `{d['medals_count']}`\n"
        f"⭐ Репутация: `{d['reputation']}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_medals(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Топ по репутации."""
    lb = api_get("/sbt/leaderboard")
    if not lb or not lb.get("top"):
        await update.message.reply_text("🏅 Пока никого нет в топе")
        return

    text = "🏆 *Топ по репутации*\n\n"
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    for i, e in enumerate(lb["top"][:10]):
        icon = medals.get(i, f"{i+1}.")
        name = f"@{e['name']}" if e.get("name") else e["address"][:12] + "..."
        text += f"{icon} {name} — `{e['reputation']}` ({e['medals']} 🏅)\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_swap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Курсы SIM-токенов."""
    pools = api_get("/swap/pools")
    if not pools or not pools.get("pools"):
        await update.message.reply_text("💱 Пулов пока нет")
        return

    text = "💱 *Пулы SIM-токенов*\n\n"
    for p in pools["pools"]:
        text += (
            f"*{p['id']}*\n"
            f"  • Резерв A: `{p['reserve_a']:.2f} {p['token_a']}`\n"
            f"  • Резерв B: `{p['reserve_b']:.2f} {p['token_b']}`\n"
            f"  • Курс: `1 {p['token_a']} = {p['price_a_in_b']:.6f} {p['token_b']}`\n\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_poc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """PoC — статистика и создание вклада."""
    stats = api_get("/poc/stats")
    if not stats:
        await update.message.reply_text("❌ PoC недоступен")
        return

    text = (
        f"🧬 *Proof of Contribution*\n\n"
        f"💰 Фонд: `{stats['pool_balance_aix']:.2f} AIX`\n"
        f"📥 Всего внесли: `{stats['total_donated_aix']:.2f} AIX`\n"
        f"📤 Всего выплат: `{stats['total_paid_aix']:.2f} AIX`\n"
        f"📋 Вкладов: `{stats['total_contributions']}`\n"
    )
    if stats.get("by_status"):
        text += "\n*По статусу:*\n"
        for status, count in stats["by_status"].items():
            text += f"  • {status}: `{count}`\n"

    # Топ контрибьюторов
    lb = api_get("/poc/leaderboard")
    if lb and lb.get("top"):
        text += "\n🏆 *Топ контрибьюторов:*\n"
        for i, e in enumerate(lb["top"][:5]):
            name = f"@{e['name']}" if e.get("name") else e["address"][:12] + "..."
            text += f"  {i+1}. {name} — `{e['reward_aix']:.2f} AIX`\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# =============================================================================
# ЗАПУСК
# =============================================================================

def main():
    if not BOT_TOKEN:
        print("❌ Не задан AIX_BOT_TOKEN")
        print()
        print("Как получить токен:")
        print("1. Открой Telegram, найди @BotFather")
        print("2. Напиши /newbot")
        print("3. Придумай имя (например, 'AIX OS Bot') и username (например, 'aix_os_bot')")
        print("4. BotFather даст токен вида '123456:ABC-DEF...'")
        print()
        print("Установи переменную окружения:")
        print('   $env:AIX_BOT_TOKEN = "твой_токен"')
        print("   python -m integrations.telegram.bot")
        sys.exit(1)

    if not check_node():
        print(f"⚠️  Нода {NODE_URL} не отвечает. Бот всё равно запустится, но команды будут выдавать ошибки.")
        print(f"   Запусти ноду: python -m network.server --port 8010 --data data/chain_A.json")
        print()

    print(f"🤖 AIX OS Bot запускается...")
    print(f"🌐 Нода: {NODE_URL}")
    print(f"🔑 Токен: {BOT_TOKEN[:20]}...")
    print()

    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("connect", cmd_connect))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CommandHandler("gift", cmd_gift))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("medals", cmd_medals))
    app.add_handler(CommandHandler("swap", cmd_swap))
    app.add_handler(CommandHandler("poc", cmd_poc))

    print("✅ Бот запущен! Открой Telegram и найди своего бота.")
    print("   Нажми /start")
    print()
    print("⏹  Для остановки: Ctrl+C")
    print()

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()