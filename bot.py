import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Отримання токена з змінної середовища
TOKEN = os.getenv("7920088294:AAFeENRxSRE8vKLJjfzI1Q-7B4VxdIRqoqY")

# Словник для зберігання бронювань (ключ - дата, значення - список заброньованих годин)
schedule_data = {}
selected_day = {}

# Словник для перекладу днів тижня
DAYS_OF_WEEK = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб"}

# Генерація клавіатури з днями тижня (з понеділка по суботу)
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range(7 - today.weekday())
        if (today + timedelta(days=i)).weekday() != 6  # виключаємо неділю
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Генерація клавіатури з доступними годинами з інтервалом у 30 хвилин
def generate_time_keyboard():
    hours = [f"{hour:02d}:{minute:02d}" for hour in range(8, 22) for minute in (0, 30)]
    keyboard = [[time] for time in hours]
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
    selected_day[update.message.chat_id] = update.message.text.strip().split(" ")[0]  # Зберігаємо обрану дату без дня тижня
    await update.message.reply_text(
        f"Ви обрали день {update.message.text}. Тепер виберіть час:",
        reply_markup=generate_time_keyboard()
    )

# Функція для обробки вибору часу та бронювання
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    message = update.message.text.strip()
    chat_id = update.message.chat_id

    try:
        # Отримуємо обраний день і час
        selected_date = selected_day.get(chat_id)
        if not selected_date:
            await update.message.reply_text("Будь ласка, спочатку оберіть день.")
            return

        booking_time = datetime.strptime(f"{selected_date} {message}", "%d.%m.%y %H:%M")
        date_str = booking_time.strftime("%d.%m.%y")
        hour = booking_time.strftime("%H:%M")

        # Перевірка доступності часу
        if date_str not in schedule_data:
            schedule_data[date_str] = []

        if hour in schedule_data[date_str]:
            await update.message.reply_text(f"Вибачте, {user_name}, цей час вже зайнято.")
            await show_available_hours(update, date_str)
        else:
            # Додаємо бронювання
            schedule_data[date_str].append(f"{hour} - {user_name}")
            await update.message.reply_text(f"Чудово, {user_name}! Ви забронювали заняття на {date_str} о {hour}.")

    except ValueError:
        await update.message.reply_text("Будь ласка, виберіть час із клавіатури.")

# Функція для показу розкладу на поточний тиждень
async def show_weekly_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now()
    week_schedule = []

    # Проходимо по днях поточного тижня (з понеділка по суботу)
    for i in range(7 - today.weekday()):
        day = today + timedelta(days=i)
        if day.weekday() == 6:  # Пропускаємо неділю
            continue
        
        date_str = day.strftime("%d.%m.%y")
        day_name = DAYS_OF_WEEK[day.weekday()]
        
        # Отримуємо бронювання на конкретний день
        if date_str in schedule_data and schedule_data[date_str]:
            day_schedule = f"{date_str} ({day_name}):\n" + "\n".join(schedule_data[date_str])
        else:
            day_schedule = f"{date_str} ({day_name}): жодних бронювань"
        
        week_schedule.append(day_schedule)

    # Відправка розкладу
    schedule_text = "\n\n".join(week_schedule)
    await update.message.reply_text(f"Розклад на тиждень:\n\n{schedule_text}")

# Функція для показу вільних годин у вибраний день
async def show_available_hours(update: Update, date_str: str) -> None:
    available_hours = [f"{hour:02d}:{minute:02d}" for hour in range(8, 22) for minute in (0, 30) if f"{hour:02d}:{minute:02d}" not in schedule_data.get(date_str, [])]
    if available_hours:
        await update.message.reply_text(f"Вільні години на {date_str}: {', '.join(available_hours)}")
    else:
        await update.message.reply_text(f"На жаль, всі години на {date_str} зайняті.")

# Основна функція для запуску бота
def main():
    print("Bot is starting...")  # Повідомлення про запуск
    application = ApplicationBuilder().token(TOKEN).build()

    # Додаємо обробник для команди /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", show_weekly_schedule))  # Команда для перегляду розкладу на тиждень

    # Обробники для вибору дня і часу
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))

    # Запускаємо бота
    application.run_polling()

if __name__ == '__main__':
    main()
