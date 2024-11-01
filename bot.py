import asyncio
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import asyncpg

# Ініціалізація змінних середовища
TELEGRAM_TOKEN = os.getenv("TOKEN")
NEON_DATABASE_URL = os.getenv("DATABASE_URL")

# Обробник команди /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Привіт! Я ваш бот для бронювання занять на барабанах.")

# Функція для обробки команди /book
async def book(update: Update, context: CallbackContext) -> None:
    try:
        # Показуємо доступні години для сьогоднішнього дня
        available_times = await get_available_times(datetime.now())
        keyboard = [[InlineKeyboardButton(time, callback_data=time)] for time in available_times]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Виберіть час для бронювання:", reply_markup=reply_markup)
    except Exception as e:
        print("Помилка у функції /book:", e)

# Функція для отримання доступних годин
async def get_available_times(date: datetime) -> list:
    hours = []
    start_hour, end_hour = 8, 20  # Години роботи бота (з 8:00 до 20:00)
    for hour in range(start_hour, end_hour):
        time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        if time > datetime.now():  # Виключаємо минулий час
            hours.append(time.strftime('%H:%M'))
    return hours

# Обробник для вибору часу з клавіатури
async def select_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    selected_time = query.data
    user_id = query.from_user.id
    booking_date = datetime.now().date()  # Дата бронювання (поточна)

    # Перевіряємо доступність вибраного часу
    if await is_time_available(booking_date, selected_time):
        # Зберігаємо бронювання у базі даних
        await save_booking(user_id, booking_date, selected_time)
        await query.edit_message_text(f"Час {selected_time} успішно заброньовано!")
    else:
        await query.edit_message_text(f"Час {selected_time} вже заброньовано. Спробуйте інший час.")

# Функція для перевірки доступності часу
async def is_time_available(date: datetime, time: str) -> bool:
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    result = await conn.fetchrow("SELECT 1 FROM bookings WHERE date=$1 AND time=$2", date, time)
    await conn.close()
    return result is None

# Функція для збереження бронювання у базі даних
async def save_booking(user_id: int, date: datetime, time: str) -> None:
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    await conn.execute("INSERT INTO bookings (user_id, date, time) VALUES ($1, $2, $3)", user_id, date, time)
    await conn.close()

# Функція для запуску бота
async def main():
    # Налаштування Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Додавання обробників команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CallbackQueryHandler(select_time))

    # Запуск бота в режимі опитування
    await application.run_polling()

# Запуск програми
if __name__ == "__main__":
    asyncio.run(main())
