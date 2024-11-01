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
    keyboard = [
        [InlineKeyboardButton("Забронювати урок", callback_data="book_lesson")],
        [InlineKeyboardButton("Мої бронювання", callback_data="my_bookings")],
        [InlineKeyboardButton("Скасувати урок", callback_data="cancel_lesson")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Виберіть дію:", reply_markup=reply_markup)

# Показ доступного часу для бронювання
async def show_available_times(query):
    available_times = await get_available_times(datetime.now())
    keyboard = [[InlineKeyboardButton(time, callback_data=f"time_{time}")] for time in available_times]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Виберіть час для бронювання:", reply_markup=reply_markup)

# Отримання доступного часу
async def get_available_times(date: datetime) -> list:
    hours = []
    start_hour, end_hour = 8, 20
    for hour in range(start_hour, end_hour):
        time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        if time > datetime.now():
            hours.append(time.strftime('%H:%M'))
    return hours

# Обробка вибору часу та підтвердження бронювання
async def handle_time_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    selected_time = query.data.split("_")[1]
    user_id = query.from_user.id
    booking_date = datetime.now().date()

    if await is_time_available(booking_date, selected_time):
        await save_booking(user_id, booking_date, selected_time)
        await query.edit_message_text(f"Час {selected_time} успішно заброньовано!")
    else:
        await query.edit_message_text(f"Час {selected_time} вже заброньовано. Спробуйте інший час.")

# Перевірка доступності часу
async def is_time_available(date: datetime, time: str) -> bool:
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    result = await conn.fetchrow("SELECT 1 FROM bookings WHERE date=$1 AND time=$2", date, time)
    await conn.close()
    return result is None

# Збереження бронювання
async def save_booking(user_id: int, date: datetime, time: str) -> None:
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    await conn.execute("INSERT INTO bookings (user_id, date, time) VALUES ($1, $2, $3)", user_id, date, time)
    await conn.close()

# Показ бронювань користувача
async def show_my_bookings(query):
    user_id = query.from_user.id
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    bookings = await conn.fetch("SELECT date, time FROM bookings WHERE user_id=$1 ORDER BY date, time", user_id)
    await conn.close()
    
    if bookings:
        text = "Ваші бронювання:\n" + "\n".join([f"{record['date']} {record['time']}" for record in bookings])
    else:
        text = "У вас немає активних бронювань."

    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

# Показ бронювань для скасування
async def show_cancel_options(query):
    user_id = query.from_user.id
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    bookings = await conn.fetch("SELECT id, date, time FROM bookings WHERE user_id=$1 ORDER BY date, time", user_id)
    await conn.close()
    
    if bookings:
        keyboard = [[InlineKeyboardButton(f"{record['date']} {record['time']}", callback_data=f"cancel_{record['id']}")] for record in bookings]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Виберіть бронювання для скасування:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("У вас немає активних бронювань для скасування.")

# Обробка скасування бронювання
async def handle_cancel_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    booking_id = int(query.data.split("_")[1])
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    await conn.execute("DELETE FROM bookings WHERE id=$1", booking_id)
    await conn.close()
    await query.edit_message_text("Ваше бронювання скасовано.")

# Функція для запуску бота у новому процесі
def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_available_times, pattern="^book_lesson$"))
    application.add_handler(CallbackQueryHandler(show_my_bookings, pattern="^my_bookings$"))
    application.add_handler(CallbackQueryHandler(show_cancel_options, pattern="^cancel_lesson$"))
    application.add_handler(CallbackQueryHandler(handle_time_selection, pattern="^time_"))
    application.add_handler(CallbackQueryHandler(handle_cancel_selection, pattern="^cancel_"))
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
