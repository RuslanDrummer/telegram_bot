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

# Словник для перекладу днів тижня
DAYS_OF_WEEK = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб"}

# Генерація основного меню
def generate_main_menu():
    keyboard = [
        ["Старт"],
        ["Бронювання вільних годин", "Скасування заняття"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з днями тижня (на 60 днів вперед)
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range(60)
        if (today + timedelta(days=i)).weekday() != 6  # виключаємо неділю
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з доступними годинами у робочому діапазоні
def generate_time_keyboard(selected_date=None):
    now = datetime.now()
    hours = [
        f"{hour:02d}:{minute:02d}"
        for hour in range(8, 20)
        for minute in (0, 30)
        if not selected_date or (selected_date != now.strftime("%d.%m.%y") or datetime(now.year, now.month, now.day, hour, minute) > now)
    ]
    keyboard = [[time] for time in hours]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з вибором тривалості
def generate_duration_keyboard():
    keyboard = [
        ["1 година", "1.5 години", "2 години"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Функція для команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вітаю! Оберіть дію:",
        reply_markup=generate_main_menu()
    )

# Функція для бронювання
async def handle_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Виберіть день для заняття:",
        reply_markup=generate_day_keyboard()
    )

# Функція для скасування бронювання
async def handle_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_bookings = [
        f"{date} {hour}"
        for date, bookings in schedule_data.items()
        for hour, booking_user in bookings.items()
        if booking_user == chat_id
    ]
    if user_bookings:
        keyboard = [[booking] for booking in user_bookings]
        await update.message.reply_text("Виберіть заняття для скасування:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    else:
        await update.message.reply_text("У вас немає заброньованих занять для скасування.")

# Обробка вибору часу
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.strip()
    chat_id = update.message.chat_id

    try:
        selected_date = selected_day.get(chat_id)
        if not selected_date:
            await update.message.reply_text("Будь ласка, спочатку оберіть день.")
            return

        booking_time = datetime.strptime(f"{selected_date} {message}", "%d.%m.%y %H:%M")
        date_str = booking_time.strftime("%d.%m.%y")
        hour = booking_time.strftime("%H:%M")

        if date_str not in schedule_data:
            schedule_data[date_str] = {}

        if hour in schedule_data[date_str]:
            await update.message.reply_text("Цей час вже зайнятий, оберіть інший.")
            await update.message.reply_text(f"Вільні години на {date_str}:", reply_markup=generate_time_keyboard(selected_date))
        else:
            schedule_data[date_str][hour] = chat_id
            await update.message.reply_text(f"Ви успішно забронювали заняття на {date_str} о {hour}.")
    except ValueError:
        await update.message.reply_text("Будь ласка, виберіть час із клавіатури.")

# Функція для обробки скасування заняття
async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.strip()
    chat_id = update.message.chat_id
    date_time = message.split()

    if len(date_time) == 2:
        date_str, hour = date_time
        if date_str in schedule_data and hour in schedule_data[date_str] and schedule_data[date_str][hour] == chat_id:
            booking_time = datetime.strptime(f"{date_str} {hour}", "%d.%m.%y %H:%M")
            hours_until_booking = (booking_time - datetime.now()).total_seconds() / 3600

            if hours_until_booking >= 12:
                del schedule_data[date_str][hour]
                await update.message.reply_text("Ваше заняття скасовано.")
            else:
                await update.message.reply_text("Скасувати можна мінімум за 12 годин. Вам потрібно буде оплатити оренду 200 грн на карту 5375411509960642.")
        else:
            await update.message.reply_text("Не знайдено бронювання.")
    else:
        await update.message.reply_text("Невірний формат вибору заняття для скасування.")

# Основна функція для запуску бота
def main():
    print("Bot is starting...")  # Повідомлення про запуск
    application = ApplicationBuilder().token(TOKEN).build()

    # Додаємо обробники команд та повідомлень
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text("Старт"), start))
    application.add_handler(MessageHandler(filters.Text("Бронювання вільних годин"), handle_booking))
    application.add_handler(MessageHandler(filters.Text("Скасування заняття"), handle_cancellation))

    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2} \d{2}:\d{2}$"), cancel_booking))

    application.run_polling()

if __name__ == '__main__':
    main()
