import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TOKEN")

# Data storage for bookings and selected day/time
schedule_data = {}
selected_day = {}
selected_time = {}
selected_duration = {}

# Constants for working hours
WORKING_HOURS_START = 8
WORKING_HOURS_END = 20

# Days of the week in Ukrainian
DAYS_OF_WEEK = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб"}

# Generate the main menu with persistent options
def generate_main_menu():
    keyboard = [
        [KeyboardButton("Бронювання вільних годин"), KeyboardButton("Скасування заняття")],
        [KeyboardButton("Переглянути розклад"), KeyboardButton("Старт")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Generate available days for 60 days ahead
def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y") + f" ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range(60) if (today + timedelta(days=i)).weekday() != 6  # Exclude Sundays
    ]
    keyboard = [[day] for day in days]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Generate available times based on current bookings
def generate_time_keyboard(selected_date):
    today = datetime.now()
    available_times = [
        f"{hour:02d}:{minute:02d}" for hour in range(WORKING_HOURS_START, WORKING_HOURS_END + 1)
        for minute in (0, 30)
    ]

    # Filter out already booked times and past times if selecting today
    if selected_date == today.strftime("%d.%m.%y"):
        available_times = [time for time in available_times if datetime.strptime(time, "%H:%M") > today]
    booked_times = schedule_data.get(selected_date, [])
    available_times = [time for time in available_times if time not in booked_times]
    keyboard = [[time] for time in available_times]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Generate duration options
def generate_duration_keyboard():
    keyboard = [[KeyboardButton("1 год"), KeyboardButton("1.5 год"), KeyboardButton("2 год")]]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Start command handler to show the main menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Вітаю! Оберіть опцію:", reply_markup=generate_main_menu())

# Handle main menu options
async def main_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    choice = update.message.text
    if choice == "Бронювання вільних годин":
        await update.message.reply_text("Виберіть день для заняття:", reply_markup=generate_day_keyboard())
    elif choice == "Скасування заняття":
        await show_user_bookings(update, context)
    elif choice == "Переглянути розклад":
        await show_weekly_schedule(update, context)

# Handle day selection for booking
async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_day[update.message.chat_id] = update.message.text.split(" ")[0]  # Store selected date without day name
    await update.message.reply_text("Тепер виберіть час:", reply_markup=generate_time_keyboard(selected_day[update.message.chat_id]))

# Handle time selection and prompt for duration
async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    selected_time[update.message.chat_id] = update.message.text.strip()
    await update.message.reply_text("Оберіть тривалість заняття:", reply_markup=generate_duration_keyboard())

# Handle duration selection and finalize booking
async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    selected_duration[user_id] = update.message.text
    selected_date = selected_day.get(user_id)
    selected_hour = selected_time.get(user_id)

    if not selected_date or not selected_hour:
        await update.message.reply_text("Помилка бронювання. Спробуйте ще раз.", reply_markup=generate_main_menu())
        return

    # Finalize booking if the slot is free
    if selected_hour not in schedule_data.get(selected_date, []):
        if selected_date not in schedule_data:
            schedule_data[selected_date] = []
        schedule_data[selected_date].append(selected_hour)
        await update.message.reply_text(
            f"Ви забронювали заняття на {selected_date} о {selected_hour} на {selected_duration[user_id]}.\n"
            "Увага: Скасування можливо не пізніше ніж за 12 годин до заняття.",
            reply_markup=generate_main_menu()
        )
    else:
        await update.message.reply_text("Цей час вже зайнятий. Оберіть інший час.", reply_markup=generate_time_keyboard(selected_date))

# Show the user's current bookings with a cancel option
async def show_user_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    user_bookings = [
        f"{date} о {time}" for date, times in schedule_data.items() for time in times
        if times and time in times
    ]
    if user_bookings:
        keyboard = [[KeyboardButton(f"Скасувати {booking}")] for booking in user_bookings]
        await update.message.reply_text("Ваші заброньовані заняття:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text("У вас немає заброньованих занять.", reply_markup=generate_main_menu())

# Cancel booking and notify about cancellation fee if late
async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    cancellation_request = update.message.text.replace("Скасувати ", "")
    date_str, time_str = cancellation_request.split(" о ")
    booking_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%y %H:%M")

    # Check if cancellation is within allowed time
    if booking_time - datetime.now() < timedelta(hours=12):
        await update.message.reply_text("Скасування пізніше ніж за 12 годин. Потрібно сплатити оренду 200 грн на карту 5375411509960642.")
    else:
        schedule_data[date_str].remove(time_str)
        await update.message.reply_text("Ваше заняття успішно скасовано.", reply_markup=generate_main_menu())

# Show weekly schedule
async def show_weekly_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now()
    week_schedule = [
        f"{(today + timedelta(days=i)).strftime('%d.%m.%y')} ({DAYS_OF_WEEK[(today + timedelta(days=i)).weekday()]})"
        for i in range(7 - today.weekday()) if (today + timedelta(days=i)).weekday() != 6
    ]
    await update.message.reply_text(f"Розклад на тиждень:\n{', '.join(week_schedule)}", reply_markup=generate_main_menu())

# Main function to start the bot
def main():
    print("Bot is starting...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^(Бронювання вільних годин|Скасування заняття|Переглянути розклад|Старт)$"), main_menu_selection))
    
    # Booking handlers
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^(1 год|1.5 год|2 год)$"), handle_duration_selection))
    
    # Cancellation handlers
    application.add_handler(MessageHandler(filters.Regex("^Скасувати"), cancel_booking))

    # Run bot
    application.run_polling()

if __name__ == '__main__':
    main()
