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
    # Відповідь користувачу при виклику команди /start
    await update.message.reply_text("Привіт! Я ваш бот.")

# Основна функція для запуску бота та налаштування підключення до бази даних
async def main():
    # Підключення до бази даних Neon
    db_connection = await asyncpg.connect(NEON_DATABASE_URL)
    
    # Налаштовуємо Telegram Application з використанням токена
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Додаємо обробник команд - при введенні /start викликається функція start
    application.add_handler(CommandHandler("start", start))
    
    # Запускаємо бота у режимі опитування, щоб він постійно працював і відповідав на команди
    await application.run_polling()

    # Закриваємо з'єднання з базою даних після завершення роботи
    await db_connection.close()

# Перевірка на активний цикл подій
try:
    # Якщо вже є активний цикл подій, запускаємо main у ньому
    asyncio.get_running_loop().run_until_complete(main())
except RuntimeError:  # Якщо активного циклу подій немає
    # Запускаємо новий цикл подій для виконання функції main
    asyncio.run(main())
