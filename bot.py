import asyncio
import concurrent.futures
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import asyncpg

# Ініціалізація змінних середовища
TELEGRAM_TOKEN = os.getenv("TOKEN")
NEON_DATABASE_URL = os.getenv("DATABASE_URL")

# Обробник команди /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Привіт! Я ваш бот.")

# Отримати доступні години для бронювання
async def get_available_times(date):
    # Ваша логіка отримання доступних годин на основі бази даних
    # Приклад: повертає список доступних годин для вказаної дати
    all_times = ["08:00", "09:30", "11:00", "13:00", "14:30", "16:00", "17:30", "19:00"]
    booked_times = await get_booked_times(date)
    available_times = [time for time in all_times if time not in booked_times]
    return available_times

async def get_booked_times(date):
    # Приклад: імітація отримання годин, які вже заброньовані з бази даних
    # Замініть на логіку запиту до бази даних
    return ["09:30", "13:00"]  # Приклад зайнятих годин

# Показ доступних днів та годин для бронювання
async def show_available_days(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Визначаємо наступні 5 днів для вибору
    days = [(datetime.now() + timedelta(days=i)) for i in range(5)]
    keyboard = []
    for day in days:
        day_label = day.strftime("%a %d-%m")  # Наприклад, "Чт 02-11"
        keyboard.append([InlineKeyboardButton(day_label, callback_data=f"date_{day.strftime('%Y-%m-%d')}")])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Виберіть день для бронювання:", reply_markup=reply_markup)

# Показ доступних годин для вибраного дня
async def show_available_times(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Отримуємо вибрану дату з callback_data
    selected_date = query.data.split("_")[1]
    available_times = await get_available_times(selected_date)

    keyboard = [[InlineKeyboardButton(time, callback_data=f"time_{selected_date}_{time}")] for time in available_times]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_days")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Виберіть час для бронювання:", reply_markup=reply_markup)

# Вибір тривалості бронювання
async def select_duration(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Отримуємо вибрану дату і час з callback_data
    selected_date, selected_time = query.data.split("_")[1:]
    context.user_data["selected_date"] = selected_date
    context.user_data["selected_time"] = selected_time

    # Пропонуємо варіанти тривалості
    keyboard = [
        [InlineKeyboardButton("1 година", callback_data="duration_1")],
        [InlineKeyboardButton("1.5 години", callback_data="duration_1.5")],
        [InlineKeyboardButton("2 години", callback_data="duration_2")],
        [InlineKeyboardButton("Назад", callback_data=f"time_{selected_date}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Виберіть тривалість для бронювання:", reply_markup=reply_markup)

# Підтвердження бронювання
async def confirm_booking(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Отримуємо вибрану тривалість
    selected_duration = query.data.split("_")[1]
    selected_date = context.user_data["selected_date"]
    selected_time = context.user_data["selected_time"]

    # Збереження бронювання в базі даних (замініть на свою логіку)
    await save_booking(selected_date, selected_time, selected_duration)

    await query.edit_message_text(
        f"Бронювання підтверджено на {selected_date} о {selected_time} тривалістю {selected_duration} годин."
    )

# Збереження бронювання (імітація)
async def save_booking(date, time, duration):
    # Ваша логіка для збереження бронювання в базі даних
    pass

# Функція для запуску бота у новому процесі
def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_available_days, pattern="^book_lesson$"))
    application.add_handler(CallbackQueryHandler(show_available_times, pattern="^date_"))
    application.add_handler(CallbackQueryHandler(select_duration, pattern="^time_"))
    application.add_handler(CallbackQueryHandler(confirm_booking, pattern="^duration_"))

    application.run_polling()

# Асинхронна функція для запуску основної програми
async def main():
    db_connection = await asyncpg.connect(NEON_DATABASE_URL)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, run_bot)

    await db_connection.close()

# Запуск програми
if __name__ == "__main__":
    asyncio.run(main())
