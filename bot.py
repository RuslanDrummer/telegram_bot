import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Отримання токена з змінної середовища
TOKEN = os.getenv("TOKEN")

# Словник для зберігання бронювань
schedule_data = {}
selected_day = {}
selected_time = {}

# Генерація клавіатури з днями для вибору на 2 місяці вперед
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y")
        for i in range(60)
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з доступними годинами
def generate_time_keyboard(selected_date=None):
    now = datetime.now()
    hours = []
    for hour in range(8, 22):
        for minute in (0, 30):
            time_str = f"{hour:02d}:{minute:02d}"
            if selected_date == now.strftime("%d.%m.%y"):
                booking_time = datetime.strptime(f"{selected_date} {time_str}", "%d.%m.%y %H:%M")
                if booking_time > now:
                    hours.append(time_str)
            else:
                hours.append(time_str)
    keyboard = [[time] for time in hours]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури для вибору тривалості заняття
def generate_duration_keyboard():
    durations = ["1 год", "1.5 год", "2 год"]
    keyboard = [[duration] for duration in durations]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f'Привіт, {user_name}! Виберіть день для заняття (відміна за 12 год до початку):',
        reply_markup=generate_day_keyboard()
    )

# Обробник вибору дня
async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_day[update.message.chat_id] = update.message.text.strip()
    await update.message.reply_text("Тепер виберіть час:", reply_markup=generate_time_keyboard(selected_day[update.message.chat_id]))

# Обробник вибору часу
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_time[update.message.chat_id] = update.message.text.strip()
    await update.message.reply_text("Оберіть тривалість заняття:", reply_markup=generate_duration_keyboard())

# Обробник вибору тривалості та підтвердження бронювання
async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    duration = update.message.text.strip()
    selected_date = selected_day.get(chat_id)
    selected_hour = selected_time.get(chat_id)

    if not selected_date or not selected_hour:
        await update.message.reply_text("Будь ласка, почніть спочатку, використовуючи команду /start.")
        return

    booking_time = datetime.strptime(f"{selected_date} {selected_hour}", "%d.%m.%y %H:%M")
    date_str = booking_time.strftime("%d.%m.%y")
    hour_str = f"{selected_hour} ({duration})"

    if date_str not in schedule_data:
        schedule_data[date_str] = {}

    if hour_str in schedule_data[date_str]:
        await update.message.reply_text(f"Час {selected_hour} вже зайнятий.")
    else:
        schedule_data[date_str][hour_str] = f"{user_name} (@{update.message.from_user.username})"
        await update.message.reply_text(
            f"Заняття заброньовано на {date_str} о {selected_hour} на {duration}. "
            "Відміна можлива мінімум за 12 годин до заняття."
        )

# Команда /cancel для відміни заняття
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    now = datetime.now()
    
    user_bookings = [
        (date, hour) for date, bookings in schedule_data.items() 
        for hour, name in bookings.items() if name.startswith(user_name)
    ]

    if not user_bookings:
        await update.message.reply_text("Не знайдено активних бронювань для відміни.")
        return

    for date, hour in user_bookings:
        booking_time = datetime.strptime(f"{date} {hour.split()[0]}", "%d.%m.%y %H:%M")
        if booking_time - now > timedelta(hours=12):
            del schedule_data[date][hour]
            await update.message.reply_text(f"Ваше заняття на {date} о {hour} скасовано.")
        else:
            await update.message.reply_text(
                f"Заняття на {date} о {hour} не можна скасувати пізніше, ніж за 12 годин до початку. "
                "Для відміни необхідно оплатити оренду 200 грн. "
                "Оплатіть, будь ласка, на карту 5375411509960642."
            )

# Основна функція для запуску бота
def main():
    print("Bot is starting...")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}$"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d\.\d год$"), handle_duration_selection))
    application.run_polling()

if __name__ == '__main__':
    main()
