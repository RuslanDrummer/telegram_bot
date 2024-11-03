import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Підключення до бази даних
conn = sqlite3.connect('schedule.db', check_same_thread=False)
cursor = conn.cursor()

# Створення таблиць для бронювань та користувачів
cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    date TEXT,
                    time TEXT,
                    duration REAL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    role TEXT)''')

conn.commit()

# Змінні для робочих годин
WORKING_HOURS_START = 8
WORKING_HOURS_END = 20

# Отримання токена з змінної середовища
TOKEN = os.getenv("TOKEN")

# Додавання користувачів
def add_user(user_id, username, role):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, role) VALUES (?, ?, ?)", (user_id, username, role))
    conn.commit()

# Функція для команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    add_user(user.id, user.username, "student")
    keyboard = [["🔔 Забронювати", "📅 Мої бронювання", "❌ Скасувати"], ["/start"]]
    await update.message.reply_text(
        "Привіт! Ви можете:\n"
        "🔔 Забронювати час\n"
        "📅 Мої бронювання\n"
        "❌ Скасувати бронювання",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# Перевірка ролі користувача
def is_teacher(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == "teacher"

# Функція для зміни робочих годин
async def sethours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_teacher(update.effective_user.id):
        try:
            start, end = map(int, context.args)
            global WORKING_HOURS_START, WORKING_HOURS_END
            WORKING_HOURS_START, WORKING_HOURS_END = start, end
            await update.message.reply_text(f"Робочі години змінені на {start}:00 - {end}:00.")
        except ValueError:
            await update.message.reply_text("Введіть початкову і кінцеву годину, наприклад: /sethours 8 20")
    else:
        await update.message.reply_text("Вибачте, ця команда доступна лише для вчителя.")

# Функція для бронювання
async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Виберіть день для заняття:", reply_markup=generate_day_keyboard())

def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'][(today + timedelta(days=i)).weekday()]})"
        for i in range(30) if (today + timedelta(days=i)).weekday() != 6
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_date = update.message.text.split()[0]
    context.user_data["selected_date"] = selected_date
    await update.message.reply_text("Виберіть час:", reply_markup=generate_time_keyboard(selected_date))

def generate_time_keyboard(selected_date):
    today = datetime.now().strftime("%d.%m.%y")
    booked_times = get_booked_times(selected_date)
    hours = [f"{hour:02d}:00" for hour in range(WORKING_HOURS_START, WORKING_HOURS_END)]
    if selected_date == today:
        current_hour = datetime.now().hour
        hours = [time for time in hours if int(time.split(":")[0]) > current_hour]
    available_hours = [time for time in hours if time not in booked_times]
    keyboard = [[time] for time in available_hours]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Отримання заброньованих часів для дати
def get_booked_times(date):
    cursor.execute("SELECT time, duration FROM bookings WHERE date=?", (date,))
    bookings = cursor.fetchall()
    booked_times = []
    for time, duration in bookings:
        start_time = datetime.strptime(f"{date} {time}", "%d.%m.%y %H:%M")
        booked_interval = [start_time + timedelta(minutes=30 * i) for i in range(int(duration * 2))]
        booked_times.extend([time.strftime("%H:%M") for time in booked_interval])
    return booked_times

# Логіка для завершення бронювання
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["selected_time"] = update.message.text
    await update.message.reply_text("Оберіть тривалість:", reply_markup=generate_duration_keyboard())

def generate_duration_keyboard():
    durations = ["1 год", "1.5 год", "2 год"]
    keyboard = [[duration] for duration in durations]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Завершення бронювання з тривалістю
async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    selected_duration = update.message.text
    duration_hours = 1 if selected_duration == "1 год" else 1.5 if selected_duration == "1.5 год" else 2
    selected_time = context.user_data["selected_time"]
    selected_date = context.user_data["selected_date"]

    cursor.execute("SELECT * FROM bookings WHERE date=? AND time=?", (selected_date, selected_time))
    if cursor.fetchone():
        await update.message.reply_text("Цей час вже зайнято.")
        return

    cursor.execute("INSERT INTO bookings (user_id, username, date, time, duration) VALUES (?, ?, ?, ?, ?)",
                   (user.id, user.username, selected_date, selected_time, duration_hours))
    conn.commit()
    await update.message.reply_text(f"Ви забронювали заняття на {selected_date} о {selected_time} на {selected_duration}.")

# Функція для перегляду бронювань користувача
async def view_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cursor.execute("SELECT date, time, duration FROM bookings WHERE user_id=?", (user_id,))
    bookings = cursor.fetchall()

    if bookings:
        booking_text = "\n".join([f"{date} о {time} (Тривалість: {duration} год)" for date, time, duration in bookings])
        await update.message.reply_text(f"Ваші бронювання:\n{booking_text}")
    else:
        await update.message.reply_text("У вас немає активних бронювань.")

# Функція для скасування бронювання
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cursor.execute("SELECT id, date, time FROM bookings WHERE user_id=?", (user_id,))
    bookings = cursor.fetchall()

    if bookings:
        keyboard = [[f"{date} о {time}"] for _, date, time in bookings]
        keyboard.append(["Назад"])
        await update.message.reply_text("Виберіть заняття для скасування:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        context.user_data["cancel_bookings"] = bookings
    else:
        await update.message.reply_text("У вас немає активних бронювань.")

# Обробка вибору для скасування
async def handle_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_booking = update.message.text
    if selected_booking == "Назад":
        await start(update, context)
        return

    for booking_id, date, time in context.user_data.get("cancel_bookings", []):
        if f"{date} о {time}" == selected_booking:
            booking_datetime = datetime.strptime(f"{date} {time}", "%d.%m.%y %H:%M")
            time_difference = (booking_datetime - datetime.now()).total_seconds() / 3600
            if time_difference < 12:
                await update.message.reply_text("Скасування можливе не менше, ніж за 12 годин. Будь ласка, оплатіть оренду в розмірі 200 грн на картку 5375411509960642.")
            else:
                cursor.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
                conn.commit()
                await update.message.reply_text(f"Ваше заняття на {date} о {time} скасовано.")
            break
    else:
        await update.message.reply_text("Забронювання не знайдено.")

# Основна функція для запуску бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sethours", sethours))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("view_bookings", view_bookings))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}$"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d+ год$"), handle_duration_selection))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Скасувати$"), handle_cancellation))

    application.run_polling()

if __name__ == '__main__':
    main()
