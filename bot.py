import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import asyncpg

# Ініціалізація змінних середовища
TELEGRAM_TOKEN = os.getenv("TOKEN")
NEON_DATABASE_URL = os.getenv("DATABASE_URL")

# Обробник команди /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Привіт! Я ваш бот.")

# Асинхронна функція для запуску бота
async def bot_task():
    # Підключення до бази даних
    db_connection = await asyncpg.connect(NEON_DATABASE_URL)
    
    # Налаштування Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    # Запуск бота в режимі опитування
    await application.initialize()
    await application.start()
    try:
        await application.run_polling()
    finally:
        # Закриття з'єднання з базою даних і завершення роботи бота
        await application.stop()
        await application.shutdown()
        await db_connection.close()

# Основний цикл для запуску програми
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(bot_task())
loop.run_forever()
