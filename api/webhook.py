import os
import json
import random
import string
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from fastapi import FastAPI, Request

load_dotenv()

DATA_FILE = "url_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"urls": {}, "stats": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_short_code(length=6):
    """Генерация короткого кода"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

app = FastAPI()

bot_app = None

def get_bot_app():
    global bot_app
    if bot_app is None:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found")
        bot_app = Application.builder().token(token).build()
        
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CallbackQueryHandler(handle_callback))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    return bot_app

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    keyboard = [
        [InlineKeyboardButton("🔗 Сократить ссылку", callback_data="shorten_url")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔗 Бот для сокращения ссылок\n\n"
        "Просто отправьте мне любую ссылку, "
        "и я создам для неё короткий адрес.\n\n"
        "Возможности:\n"
        "• Сокращение ссылок\n"
        "• Кастомные алиасы\n"
        "• Статистика кликов\n"
        "• QR-коды",
        reply_markup=reply_markup
    )

async def shorten_url_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню сокращения ссылок"""
    keyboard = [
        [InlineKeyboardButton("🎲 Случайный код", callback_data="random_code")],
        [InlineKeyboardButton("✏️ Кастомный код", callback_data="custom_code")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_text(
        "🔗 Сокращение ссылки\n\n"
        "Выберите тип сокращения:\n\n"
        "• Случайный код - автоматически генерируется\n"
        "• Кастомный код - выберите свой код",
        reply_markup=reply_markup
    )

async def random_code_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим случайного кода"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="shorten_url")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_text(
        "🎲 Случайный код\n\n"
        "Просто отправьте мне ссылку, "
        "и я автоматически создам короткий код.\n\n"
        "Пример: https://example.com/very-long-url",
        reply_markup=reply_markup
    )
    
    context.user_data['mode'] = 'random'

async def custom_code_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Режим кастомного кода"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="shorten_url")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_text(
        "✏️ Кастомный код\n\n"
        "Отправьте ссылку в формате:\n"
        "ссылка код\n\n"
        "Пример:\n"
        "https://example.com mylink\n\n"
        "Код должен содержать только буквы и цифры (3-10 символов)",
        reply_markup=reply_markup
    )
    
    context.user_data['mode'] = 'custom'

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика пользователя"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = load_data()
    
    user_urls = {k: v for k, v in data['urls'].items() if v['user_id'] == user_id}
    
    text = "📊 Ваша статистика\n\n"
    text += f"🔗 Всего ссылок: {len(user_urls)}\n"
    
    total_clicks = sum(v.get('clicks', 0) for v in user_urls.values())
    text += f"👆 Всего кликов: {total_clicks}\n\n"
    
    if user_urls:
        text += "📋 Ваши ссылки:\n\n"
        for code, url_data in list(user_urls.items())[:5]:
            text += f"• /{code}\n"
            text += f"  Кликов: {url_data.get('clicks', 0)}\n"
            text += f"  Создано: {url_data.get('created', 'N/A')}\n\n"
        
        if len(user_urls) > 5:
            text += f"... и ещё {len(user_urls) - 5} ссылок"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию"""
    query = update.callback_query
    
    text = "ℹ️ Информация о боте\n\n"
    text += "🔗 Бот для сокращения ссылок\n\n"
    text += "Возможности:\n"
    text += "• Быстрое сокращение длинных ссылок\n"
    text += "• Кастомные алиасы для запоминания\n"
    text += "• Статистика кликов по каждой ссылке\n"
    text += "• QR-коды для ссылок\n\n"
    text += "Использование:\n"
    text += "1. Просто отправьте ссылку\n"
    text += "2. Получите короткий код\n"
    text += "3. Отправляйте /код для расшифровки\n\n"
    text += "Связь с разработчиком: @eacmiss"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ссылок"""
    user_id = str(update.effective_user.id)
    data = load_data()
    mode = context.user_data.get('mode', 'random')
    
    message_text = update.message.text.strip()
    
    if message_text.startswith('/'):
        code = message_text[1:]
        if code in data['urls']:
            url_data = data['urls'][code]
            text = f"🔗 Расшифровка ссылки\n\n"
            text += f"Код: /{code}\n"
            text += f"Оригинальная ссылка: {url_data['original_url']}\n"
            text += f"Кликов: {url_data.get('clicks', 0)}\n"
            text += f"Создана: {url_data.get('created', 'N/A')}"
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("⚠️ Ссылка с таким кодом не найдена")
        return
    
    if mode == 'custom':
        parts = message_text.split(maxsplit=1)
        if len(parts) == 2:
            url, custom_code = parts
            custom_code = custom_code.strip()
            
            if not custom_code.isalnum() or len(custom_code) < 3 or len(custom_code) > 10:
                await update.message.reply_text(
                    "⚠️ Неверный формат кода.\n"
                    "Код должен содержать только буквы и цифры (3-10 символов)"
                )
                return
            
            if custom_code in data['urls']:
                await update.message.reply_text("⚠️ Этот код уже занят")
                return
            
            short_code = custom_code
        else:
            await update.message.reply_text(
                "⚠️ Неверный формат.\n"
                "Используйте: ссылка код\n"
                "Пример: https://example.com mylink"
            )
            return
    else:
        url = message_text
        while True:
            short_code = generate_short_code()
            if short_code not in data['urls']:
                break
    
    if not (url.startswith('http://') or url.startswith('https://')):
        await update.message.reply_text("⚠️ Ссылка должна начинаться с http:// или https://")
        return
    
    data['urls'][short_code] = {
        'original_url': url,
        'user_id': user_id,
        'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'clicks': 0
    }
    save_data(data)
    
    await update.message.reply_text(
        f"✅ Ссылка сокращена!\n\n"
        f"🔗 Код: /{short_code}\n"
        f"📝 Оригинал: {url}\n\n"
        f"Отправьте /{short_code} чтобы увидеть оригинальную ссылку"
    )
    
    context.user_data['mode'] = 'random'

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    keyboard = [
        [InlineKeyboardButton("🔗 Сократить ссылку", callback_data="shorten_url")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_text(
        "🔗 Бот для сокращения ссылок\n\n"
        "Просто отправьте мне любую ссылку, "
        "и я создам для неё короткий адрес.\n\n"
        "Возможности:\n"
        "• Сокращение ссылок\n"
        "• Кастомные алиасы\n"
        "• Статистика кликов\n"
        "• QR-коды",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback запросов"""
    query = update.callback_query
    data = query.data
    
    if data == "shorten_url":
        await shorten_url_menu(update, context)
    elif data == "random_code":
        await random_code_mode(update, context)
    elif data == "custom_code":
        await custom_code_mode(update, context)
    elif data == "my_stats":
        await my_stats(update, context)
    elif data == "info":
        await show_info(update, context)
    elif data == "back_main":
        await back_main(update, context)

@app.post("/webhook")
async def webhook(request: Request):
    """Обработка Telegram webhook"""
    application = get_bot_app()
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "url-shortener-bot is running"}
