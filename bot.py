import os
import logging
import asyncpg
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("123456789:ABCDefGHIJKLMNOPQRSTUVWXYZ")
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
    pool = await create_db_pool()
    await initialize_db(pool)

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()  # Ініціалізуємо додаток
    await application.start()  # Запускаємо додаток
    await application.run_polling()  # Запускаємо обробку подій без явного закриття циклу

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())  # Запускаємо без створення конфліктів циклу подій
    except RuntimeError as e:
        logging.error(f"RuntimeError: {e}")
