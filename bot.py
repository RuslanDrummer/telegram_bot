import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import asyncpg  # бібліотека для роботи з базою даних PostgreSQL

# Ініціалізуємо змінні середовища для отримання токену бота та URL бази даних
TELEGRAM_TOKEN = os.getenv("TOKEN")  # Токен Telegram бота
NEON_DATABASE_URL = os.getenv("DATABASE_URL")  # URL бази даних Neon

# Функція обробника команди /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Привіт! Я ваш бот.")

# Основна функція для запуску бота та налаштування підключення до бази даних
async def main():
    # Підключення до бази даних Neon
    db_connection = await asyncpg.connect(NEON_DATABASE_URL)
    
    # Налаштовуємо Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Додаємо обробник команди
    application.add_handler(CommandHandler("start", start))
    
    # Запускаємо бота у режимі опитування без закриття основного циклу подій
    await application.initialize()
    await application.start()
    await application.run_polling()
    
    # Закриваємо з'єднання з базою даних при завершенні роботи
    await db_connection.close()

if __name__ == "__main__":
    # Запуск основної функції в існуючому циклі подій або створення нового
    asyncio.run(main())
