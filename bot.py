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
selected_time_slot = {}

# Словник для перекладу днів тижня
DAYS_OF_WEEK = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб"}

# Генерація клавіатури з днями для бронювання на 60 днів вперед
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range(60)
        if (today + timedelta(days=i)).weekday() != 6  # виключаємо неділю
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з доступними годинами з інтервалом у 30 хвилин
def generate_time_keyboard(selected_date):
    today = datetime.now()
    selected_date_obj = datetime.strptime(selected_date, "%d.%m.%y")
    start_hour = today.hour if selected_date_obj.date() == today.date() else 8

    hours = [
        f"{hour:02d}:{minute:02d}" for hour in range(start_hour, 22) for minute in (0, 30)
        if selected_date_obj.date() > today.date() or (hour > today.hour or (hour == today.hour and minute > today.minute))
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
        f'Привіт, {user_name}! Виберіть день для заняття. Відміна заняття можлива не пізніше ніж за 12 годин до початку:',
        reply_markup=generate_day_keyboard()
    )

# Обробник для вибору дня
async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    selected_day[update.message.chat_id] = update.message.text.strip().split(" ")[0]  # Зберігаємо обрану дату без дня тижня
    await update.message.reply_text(
        f"Ви обрали день {update.message.text}. Тепер виберіть час:",
        reply_markup=generate_time_keyboard(selected_day[update.message.chat_id])
    )

# Обробник для вибору часу
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    message = update.message.text.strip()
    chat_id = update.message.chat_id

    selected_date = selected_day.get(chat_id)
    if not selected_date:
        await update.message.reply_text("Будь ласка, спочатку оберіть день.")
        return

    selected_time_slot[chat_id] = message
    await update.message.reply_text(
        "Оберіть тривалість заняття:",
        reply_markup=generate_duration_keyboard()
    )

# Функція для обробки вибору тривалості заняття
async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    user_nickname = f"@{update.message.from_user.username}" if update.message.from_user.username else "без нікнейму"
    duration = update.message.text.strip()
    chat_id = update.message.chat_id

    selected_date = selected_day.get(chat_id)
    selected_time = selected_time_slot.get(chat_id)
    if not selected_date or not selected_time:
        await update.message.reply_text("Спершу оберіть день та час.")
        return

    booking_time = datetime.strptime(f"{selected_date} {selected_time}", "%d.%m.%y %H:%M")
    end_time = booking_time + timedelta(hours=float(duration.split()[0]))
    date_str = booking_time.strftime("%d.%m.%y")
    time_slot = f"{selected_time} - {end_time.strftime('%H:%M')}"

    # Перевірка доступності
    if date_str not in schedule_data:
        schedule_data[date_str] = []

    if any(time_slot in b for b in schedule_data[date_str]):
        await update.message.reply_text(f"Час {time_slot} вже зайнятий.")
        await show_available_hours(update, date_str)
    else:
        booking_entry = f"{time_slot} - {user_name} ({user_nickname})"
        schedule_data[date_str].append(booking_entry)
        await update.message.reply_text(
            f"Ваше заняття заброньовано на {date_str}, {time_slot}. "
            "Відміна заняття можлива не пізніше ніж за 12 годин до початку."
        )

# Функція для показу всіх бронювань з нікнеймами
async def show_all_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not schedule_data:
        await update.message.reply_text("Жодних бронювань немає.")
        return

    all_bookings = []
    for date, bookings in schedule_data.items():
        day_bookings = f"{date}:\n" + "\n".join(bookings)
        all_bookings.append(day_bookings)

    bookings_text = "\n\n".join(all_bookings)
    await update.message.reply_text(f"Усі бронювання:\n\n{bookings_text}")

# Функція для відміни бронювання
async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat_id

    if chat_id not in selected_day or chat_id not in selected_time_slot:
        await update.message.reply_text("У вас немає активних бронювань.")
        return

    selected_date = selected_day[chat_id]
    selected_time = selected_time_slot[chat_id]
    booking_time = datetime.strptime(f"{selected_date} {selected_time}", "%d.%m.%y %H:%M")
    current_time = datetime.now()

    # Перевірка часу для відміни
    if (booking_time - current_time).total_seconds() / 3600 < 12:
        await update.message.reply_text(
            "Відміна можлива лише за 12 годин до початку заняття. "
            "Будь ласка, сплатіть орендну плату у розмірі 200 грн на номер карти 5375411509960642."
        )
    else:
        date_str = booking_time.strftime("%d.%m.%y")
        time_slot = f"{selected_time} - {(booking_time + timedelta(hours=1)).strftime('%H:%M')}"
        
        # Видаляємо бронювання
        if date_str in schedule_data and time_slot in [b.split(" - ")[0] for b in schedule_data[date_str]]:
            schedule_data[date_str] = [b for b in schedule_data[date_str] if time_slot not in b]
            await update.message.reply_text(f"Ваше заняття на {date_str} о {selected_time} успішно відмінено.")
        else:
            await update.message.reply_text("Не знайдено бронювання для відміни.")

# Основна функція для запуску бота
def main():
    print("Bot is starting...")  # Повідомлення про запуск
    print("Loaded TOKEN:", TOKEN)
    application = ApplicationBuilder().token(TOKEN).build()

    # Додаємо обробник для команди /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", show_all_bookings))  # Команда для перегляду всіх бронювань
    application.add_handler(CommandHandler("cancel", cancel_booking))  # Команда для відміни бронювання

    # Обробники для вибору дня, часу і тривалості
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^(1 год|1.5 год|2 год)$"), handle_duration_selection))

    # Запускаємо бота
    application.run_polling()

if __name__ == '__main__':
    main()
