import os
import logging
import asyncpg
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def create_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def initialize_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_name VARCHAR(255),
                date DATE,
                start_time TIME,
                end_time TIME,
                duration VARCHAR(50)
            );
        """)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Натисніть 'Почати' для доступу до меню.", reply_markup=ReplyKeyboardMarkup([["Почати"]], resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Ваша відповідь обробляється.")

async def main():
    logging.info("Starting the main function")
    
    # Підключення до бази даних та ініціалізація
    pool = await create_db_pool()
    logging.info("Database pool created")
    await initialize_db(pool)
    logging.info("Database initialized")

    # Створення і конфігурація бота
    application = ApplicationBuilder().token(TOKEN).build()
    await application.initialize()  # Ініціалізуємо перед стартом
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Application handlers added")

    # Запуск бота
    await application.start()
    logging.info("Bot polling started")
    
    try:
        await application.updater.idle()  # Чекає завершення роботи
    finally:
        await application.stop()
        logging.info("Bot polling stopped")

# Основний запуск
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"An error occurred: {e}")
