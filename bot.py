import os
import logging
import asyncpg
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

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

WORKING_HOURS_START = 8
WORKING_HOURS_END = 20

# Генерація стартового меню
def generate_start_menu():
    keyboard = [["Почати"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def generate_main_menu():
    keyboard = [
        ["Забронювати вільні години"],
        ["Скасувати заняття"],
        ["Переглянути заброньовані заняття"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def generate_day_keyboard():
    today = datetime.now()
    days = [(today + timedelta(days=i)).strftime("%d.%m.%y") for i in range(60)]
    keyboard = [[day] for day in days]
    keyboard.append(["Назад"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def generate_time_keyboard(pool, selected_date):
    today = datetime.now()
    current_time = today.strftime("%H:%M")
    available_times = [
        f"{hour:02d}:{minute:02d}" for hour in range(WORKING_HOURS_START, WORKING_HOURS_END + 1)
        for minute in (0, 30)
    ]
    
    if selected_date == today.strftime("%d.%m.%y"):
        available_times = [time for time in available_times if time > current_time]

    booked_times = await get_booked_times(pool, selected_date)
    available_times = [
        time for time in available_times if not any(
            booked_start <= datetime.strptime(time, "%H:%M").time() < booked_end
            for booked_start, booked_end in booked_times
        )
    ]

    if not available_times:
        return None
    else:
        keyboard = [[time] for time in available_times]
        keyboard.append(["Назад"])
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def save_booking(pool, chat_id, user_name, selected_date, selected_time, end_time, duration):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bookings (chat_id, user_name, date, start_time, end_time, duration)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, chat_id, user_name, selected_date, selected_time, end_time, duration)

async def get_booked_times(pool, selected_date):
    async with pool.acquire() as conn:
        records = await conn.fetch("""
            SELECT start_time, end_time FROM bookings WHERE date = $1;
        """, datetime.strptime(selected_date, "%d.%m.%y").date())
        return [(record['start_time'], record['end_time']) for record in records]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Натисніть 'Почати' для доступу до меню.", reply_markup=generate_start_menu())

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, pool) -> None:
    await update.message.reply_text("Вітаю! Використовуйте меню для навігації.", reply_markup=generate_main_menu())

async def handle_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, pool) -> None:
    await update.message.reply_text("Оберіть день для заняття:", reply_markup=generate_day_keyboard())

async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, pool) -> None:
    if update.message.text == "Назад":
        await start_menu(update, context, pool)
        return

    selected_day = update.message.text
    time_keyboard = await generate_time_keyboard(pool, selected_day)

    if time_keyboard is None:
        await update.message.reply_text(
            "На обраний день більше немає доступних годин. Оберіть інший день.",
            reply_markup=generate_day_keyboard()
        )
    else:
        context.user_data['selected_day'] = selected_day
        await update.message.reply_text("Оберіть час:", reply_markup=time_keyboard)

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, pool) -> None:
    if update.message.text == "Назад":
        await handle_booking(update, context, pool)
        return

    selected_time = update.message.text
    context.user_data['selected_time'] = selected_time
    await update.message.reply_text("Оберіть тривалість заняття:", reply_markup=generate_duration_keyboard())

def generate_duration_keyboard():
    keyboard = [["1 година"], ["1.5 години"], ["2 години"], ["Назад"]]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, pool) -> None:
    if update.message.text == "Назад":
        await handle_booking(update, context, pool)
        return

    duration = update.message.text
    duration_minutes = {"1 година": 60, "1.5 години": 90, "2 години": 120}[duration]
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name

    selected_date = datetime.strptime(context.user_data['selected_day'], "%d.%m.%y").date()
    selected_time = datetime.strptime(context.user_data['selected_time'], "%H:%M").time()
    end_time = (datetime.combine(selected_date, selected_time) + timedelta(minutes=duration_minutes)).time()

    await save_booking(pool, chat_id, user_name, selected_date, selected_time, end_time, duration)
    await update.message.reply_text(
        f"Заняття заброньовано на {selected_date} о {selected_time} до {end_time}.",
        reply_markup=generate_main_menu()
    )

async def main():
    pool = await create_db_pool()
    await initialize_db(pool)

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^Почати$"), lambda update, context: start_menu(update, context, pool)))
    application.add_handler(MessageHandler(filters.Regex("^Забронювати вільні години$"), lambda update, context: handle_booking(update, context, pool)))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}$"), lambda update, context: handle_day_selection(update, context, pool)))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), lambda update, context: handle_time_selection(update, context, pool)))
    application.add_handler(MessageHandler(filters.Regex(r"^(1 година|1\.5 години|2 години)$"), lambda update, context: handle_duration_selection(update, context, pool)))

    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
