import os
import logging
import asyncpg
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "7920088294:AAFeENRxSRE8vKLJjfzI1Q-7B4VxdIRqoqY"
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

    # Створення бота та його ініціалізація
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота з функцією run_polling
    await application.initialize()
    await application.start()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
