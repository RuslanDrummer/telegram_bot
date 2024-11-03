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
    await update.message.reply_text(
        "Привіт! Ви можете:\n"
        "/book - Забронювати час\n"
        "/schedule - Переглянути розклад\n"
        "/cancel - Скасувати бронювання\n"
        "/sethours - Змінити робочі години (лише для вчителя)",
        reply_markup=ReplyKeyboardMarkup([["/book", "/schedule", "/cancel"]], resize_keyboard=True)
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
    days = [(today + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(60)]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_date = update.message.text
    context.user_data["selected_date"] = selected_date
    await update.message.reply_text("Виберіть час:", reply_markup=generate_time_keyboard(selected_date))

def generate_time_keyboard(selected_date):
    today = datetime.now().strftime("%d.%m.%Y")
    hours = [f"{hour:02d}:00" for hour in range(WORKING_HOURS_START, WORKING_HOURS_END)]
    if selected_date == today:
        current_hour = datetime.now().hour
        hours = [time for time in hours if int(time.split(":")[0]) > current_hour]
    keyboard = [[time] for time in hours]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Логіка для завершення бронювання
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    selected_time = update.message.text
    selected_date = context.user_data.get("selected_date")

    cursor.execute("SELECT * FROM bookings WHERE date=? AND time=?", (selected_date, selected_time))
    if cursor.fetchone():
        await update.message.reply_text("Цей час вже зайнято.")
        return

    cursor.execute("INSERT INTO bookings (user_id, username, date, time, duration) VALUES (?, ?, ?, ?, ?)",
                   (user.id, user.username, selected_date, selected_time, 1.0))
    conn.commit()
    await update.message.reply_text(f"Ви забронювали заняття на {selected_date} о {selected_time}.")

# Функція для скасування бронювання
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cursor.execute("SELECT id, date, time FROM bookings WHERE user_id=?", (user_id,))
    bookings = cursor.fetchall()

    if bookings:
        for booking_id, date, time in bookings:
            cursor.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
            conn.commit()
            await update.message.reply_text(f"Ваше заняття на {date} о {time} скасовано.")
    else:
        await update.message.reply_text("У вас немає активних бронювань.")

# Функція для перегляду розкладу
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cursor.execute("SELECT username, date, time FROM bookings")
    bookings = cursor.fetchall()
    if bookings:
        schedule_text = "\n".join([f"{username}: {date} о {time}" for username, date, time in bookings])
        await update.message.reply_text(f"Розклад:\n{schedule_text}")
    else:
        await update.message.reply_text("Розклад порожній.")

# Основна функція для запуску бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sethours", sethours))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{4}$"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))

    application.run_polling()

if __name__ == '__main__':
    main()
