import asyncio
import concurrent.futures
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

# Функція для запуску бота у новому процесі
def run_bot():
    # Налаштування Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # Запуск бота в режимі опитування
    application.run_polling()

# Асинхронна функція для запуску основної програми
async def main():
    # Підключення до бази даних
    db_connection = await asyncpg.connect(NEON_DATABASE_URL)
    
    # Використання ProcessPoolExecutor для запуску бота у новому процесі
    with concurrent.futures.ProcessPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, run_bot)

    # Закриття з'єднання з базою даних після завершення роботи бота
    await db_connection.close()

# Запуск програми
if __name__ == "__main__":
    asyncio.run(main())
