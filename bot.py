import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Отримання токена з змінної середовища
TOKEN = os.getenv("TOKEN")

# Словник для зберігання бронювань (ключ - дата, значення - список заброньованих годин)
schedule_data = {}
selected_day = {}
selected_duration = {}

# Словник для перекладу днів тижня
DAYS_OF_WEEK = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб"}

# Генерація клавіатури з днями (на 2 місяці вперед)
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range((today + timedelta(days=60) - today).days + 1)
        if (today + timedelta(days=i)).weekday() != 6
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з доступними годинами, з виключенням минулого часу
def generate_time_keyboard(selected_date: str):
    today = datetime.now()
    selected_date_dt = datetime.strptime(selected_date, "%d.%m.%y")
    is_today = selected_date_dt.date() == today.date()
    hours = [
        f"{hour:02d}:{minute:02d}"
        for hour in range(8, 22)
        for minute in (0, 30)
        if not (is_today and datetime(selected_date_dt.year, selected_date_dt.month, selected_date_dt.day, hour, minute) < today)
    ]
    keyboard = [[time] for time in hours]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури для вибору тривалості заняття
def generate_duration_keyboard():
    durations = ["1 год", "1.5 год", "2 год"]
    keyboard = [[duration] for duration in durations]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Функція для команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f'Привіт, {user_name}! Виберіть день для заняття:',
        reply_markup=generate_day_keyboard()
    )

# Обробник для вибору дня
async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    selected_day[update.message.chat_id] = update.message.text.strip().split(" ")[0]
    await update.message.reply_text(
        f"Ви обрали день {update.message.text}. Тепер виберіть час:",
        reply_markup=generate_time_keyboard(selected_day[update.message.chat_id])
    )

# Обробник для вибору часу
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    message = update.message.text.strip()
    
    if chat_id not in selected_day:
        await update.message.reply_text("Будь ласка, спочатку оберіть день.")
        return

    selected_duration[chat_id] = message
    await update.message.reply_text(
        f"Виберіть тривалість заняття:",
        reply_markup=generate_duration_keyboard()
    )

# Обробник для вибору тривалості заняття
async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    message = update.message.text.strip()

    try:
        selected_date = selected_day.get(chat_id)
        selected_time = selected_duration.get(chat_id)
        
        if not selected_date or not selected_time:
            await update.message.reply_text("Будь ласка, спочатку оберіть день та час.")
            return

        duration_hours = float(message.split(" ")[0])
        booking_start = datetime.strptime(f"{selected_date} {selected_time}", "%d.%m.%y %H:%M")
        booking_end = booking_start + timedelta(hours=duration_hours)

        date_str = booking_start.strftime("%d.%m.%y")
        hour_str = f"{booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}"

        if date_str not in schedule_data:
            schedule_data[date_str] = []

        if any(hour in schedule_data[date_str] for hour in hour_str.split(" - ")):
            await update.message.reply_text(f"Вибачте, {user_name}, цей час вже зайнято.")
        else:
            schedule_data[date_str].append(hour_str)
            await update.message.reply_text(f"Чудово, {user_name}! Ви забронювали заняття на {date_str} з {hour_str}.")

    except ValueError:
        await update.message.reply_text("Будь ласка, виберіть тривалість заняття із клавіатури.")

# Основна функція для запуску бота
def main():
    print("Bot is starting...")
    application = ApplicationBuilder().token(TOKEN).build()

    # Додаємо обробники для команди /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^1 год$|^1\.5 год$|^2 год$"), handle_duration_selection))

    # Запускаємо бота
    application.run_polling()

if __name__ == '__main__':
    main()
