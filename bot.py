import asyncio
import concurrent.futures
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import asyncpg

# Ініціалізація змінних середовища
TELEGRAM_TOKEN = os.getenv("TOKEN")
NEON_DATABASE_URL = os.getenv("DATABASE_URL")

# Обробник команди /start
async def start(update: Update, context: CallbackContext) -> None:
    print("Команда /start виконана")
    await update.message.reply_text("Привіт! Я ваш бот для бронювання занять на барабанах.")

# Функція для обробки команди /book
async def book(update: Update, context: CallbackContext) -> None:
    print("Команда /book виконана")
    try:
        # Показуємо доступні години для сьогоднішнього дня
        available_times = await get_available_times(datetime.now())
        print("Доступний час:", available_times)
        keyboard = [[InlineKeyboardButton(time, callback_data=time)] for time in available_times]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Виберіть час для бронювання:", reply_markup=reply_markup)
    except Exception as e:
        print("Помилка у функції /book:", e)

# Функція для отримання доступних годин
async def get_available_times(date: datetime) -> list:
    print("Отримання доступного часу")
    hours = []
    start_hour, end_hour = 8, 20  # Години роботи бота (з 8:00 до 20:00)
    for hour in range(start_hour, end_hour):
        time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        if time > datetime.now():  # Виключаємо минулий час
            hours.append(time.strftime('%H:%M'))
    print("Доступні години:", hours)
    return hours

# Обробник для вибору часу з клавіатури
async def select_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    selected_time = query.data
    user_id = query.from_user.id
    booking_date = datetime.now().date()  # Дата бронювання (поточна)

    print(f"Вибрано час {selected_time} для користувача {user_id}")
    # Перевіряємо доступність вибраного часу
    if await is_time_available(booking_date, selected_time):
        # Зберігаємо бронювання у базі даних
        await save_booking(user_id, booking_date, selected_time)
        await query.edit_message_text(f"Час {selected_time} успішно заброньовано!")
        print(f"Час {selected_time} успішно заброньовано для користувача {user_id}")
    else:
        await query.edit_message_text(f"Час {selected_time} вже заброньовано. Спробуйте інший час.")
        print(f"Час {selected_time} вже заброньовано для користувача {user_id}")

# Функція для перевірки доступності часу
async def is_time_available(date: datetime, time: str) -> bool:
    print(f"Перевірка доступності часу {time} на дату {date}")
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    result = await conn.fetchrow("SELECT 1 FROM bookings WHERE date=$1 AND time=$2", date, time)
    await conn.close()
    is_available = result is None
    print(f"Час {time} {'доступний' if is_available else 'недоступний'} на дату {date}")
    return is_available

# Функція для збереження бронювання у базі даних
async def save_booking(user_id: int, date: datetime, time: str) -> None:
    print(f"Збереження бронювання для користувача {user_id} на час {time} і дату {date}")
    conn = await asyncpg.connect(NEON_DATABASE_URL)
    await conn.execute("INSERT INTO bookings (user_id, date, time) VALUES ($1, $2, $3)", user_id, date, time)
    await conn.close()
    print(f"Бронювання для користувача {user_id} на час {time} і дату {date} збережено")

# Функція для запуску бота у новому процесі
def run_bot():
    # Налаштування Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CallbackQueryHandler(select_time))  # Обробник вибору часу
    
    # Запуск бота в режимі опитування
    application.run_polling()

# Функція для підключення до бази даних з повторними спробами
async def connect_with_retry(retries=5):
    attempt = 0
    while attempt < retries:
        try:
            db_connection = await asyncpg.connect(NEON_DATABASE_URL)
            print("Підключення до бази даних встановлено.")
            return db_connection
        except asyncpg.ConnectionDoesNotExistError:
            attempt += 1
            print(f"Спроба {attempt} не вдалася. Повторне підключення через 5 секунд...")
            await asyncio.sleep(5)
    raise Exception("Не вдалося підключитися до бази даних після кількох спроб.")

# Асинхронна функція для запуску основної програми
async def main():
    # Підключення до бази даних із повторними спробами
    db_connection = await connect_with_retry()
    
    # Використання ProcessPoolExecutor для запуску бота у новому процесі
    with concurrent.futures.ProcessPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, run_bot)

    # Закриття з'єднання з базою даних після завершення роботи бота
    await db_connection.close()

# Запуск програми
if __name__ == "__main__":
    asyncio.run(main())
