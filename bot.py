import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TOKEN")

WORKING_HOURS_START = 8
WORKING_HOURS_END = 20

schedule_data = {}
selected_day = {}

def generate_start_menu():
    keyboard = [["Почати"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def generate_main_menu():
    keyboard = [
        ["Забронювати вільні години"],
        ["Скасувати заняття"],
        ["Переглянути заброньовані заняття"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def generate_day_keyboard():
    today = datetime.now()
    days = [
        (today + timedelta(days=i)).strftime("%d.%m.%y")
        for i in range(60)
    ]
    keyboard = [[day] for day in days]
    keyboard.append(["Назад"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def generate_time_keyboard(selected_date):
    today = datetime.now()
    available_times = [
        f"{hour:02d}:{minute:02d}" for hour in range(WORKING_HOURS_START, WORKING_HOURS_END + 1)
        for minute in (0, 30)
    ]
    if selected_date == today.strftime("%d.%m.%y"):
        available_times = [time for time in available_times if datetime.strptime(time, "%H:%M") > today]

    booked_times = schedule_data.get(selected_date, [])
    available_times = [
        time for time in available_times if not any(
            booked_time <= datetime.strptime(time, "%H:%M") < (booked_time + booked_duration)
            for booked_time, booked_duration in booked_times
        )
    ]

    if not available_times:
        return None
    else:
        keyboard = [[time] for time in available_times]
        keyboard.append(["Назад"])
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def generate_duration_keyboard():
    keyboard = [["1 година"], ["1.5 години"], ["2 години"], ["Назад"]]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Натисніть 'Почати' для доступу до меню.",
        reply_markup=generate_start_menu()
    )

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вітаю! Використовуйте меню для навігації.",
        reply_markup=generate_main_menu()
    )

async def handle_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Оберіть день для заняття:",
        reply_markup=generate_day_keyboard()
    )

async def handle_day_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Назад":
        await start_menu(update, context)
        return

    selected_day[update.message.chat_id] = update.message.text
    time_keyboard = generate_time_keyboard(selected_day[update.message.chat_id])

    if time_keyboard is None:
        await update.message.reply_text(
            "На обраний день більше немає доступних годин. Оберіть інший день.",
            reply_markup=generate_day_keyboard()
        )
    else:
        await update.message.reply_text("Оберіть час:", reply_markup=time_keyboard)

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Назад":
        await handle_booking(update, context)
        return

    selected_time = update.message.text
    selected_day[update.message.chat_id] = f"{selected_day[update.message.chat_id]} {selected_time}"
    await update.message.reply_text("Оберіть тривалість заняття:", reply_markup=generate_duration_keyboard())

async def handle_duration_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Назад":
        await handle_booking(update, context)
        return

    duration = update.message.text
    duration_minutes = {"1 година": 60, "1.5 години": 90, "2 години": 120}[duration]
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name

    selected_date, selected_time = selected_day[chat_id].split(" ")
    selected_datetime = datetime.strptime(selected_time, "%H:%M")
    end_time = (selected_datetime + timedelta(minutes=duration_minutes)).strftime("%H:%M")

    if selected_date not in schedule_data:
        schedule_data[selected_date] = []

    schedule_data[selected_date].append((selected_datetime, timedelta(minutes=duration_minutes), f"{user_name} ({duration})"))
    await update.message.reply_text(
        f"Заняття заброньовано на {selected_date} о {selected_time} до {end_time}.",
        reply_markup=generate_main_menu()
    )

async def handle_view_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    booked_schedule = []

    for date, bookings in schedule_data.items():
        day_schedule = f"{date}:\n" + "\n".join([f"{time.strftime('%H:%M')} - {user}" for time, _, user in bookings])
        booked_schedule.append(day_schedule)

    if booked_schedule:
        await update.message.reply_text("Заброньовані заняття:\n" + "\n\n".join(booked_schedule))
    else:
        await update.message.reply_text("Заброньованих занять немає.", reply_markup=generate_main_menu())

async def handle_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    user_bookings = []

    for date, bookings in schedule_data.items():
        for booking in bookings:
            if user_name in booking[2]:
                user_bookings.append(f"{date} {booking[0].strftime('%H:%M')} - {booking[2]}")

    if user_bookings:
        keyboard = [[booking] for booking in user_bookings]
        keyboard.append(["Назад"])
        await update.message.reply_text("Ваші заброньовані заняття. Оберіть для скасування:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    else:
        await update.message.reply_text("У вас немає заброньованих занять.", reply_markup=generate_main_menu())

async def confirm_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "Назад":
        await handle_cancellation(update, context)
        return

    selected_booking = update.message.text
    date, time = selected_booking.split(" ", 1)
    for booking in schedule_data[date]:
        if booking[0].strftime("%H:%M") in time:
            schedule_data[date].remove(booking)
            break
    if not schedule_data[date]:
        del schedule_data[date]
        
    await update.message.reply_text("Заняття скасовано.", reply_markup=generate_main_menu())

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^Почати$"), start_menu))
    application.add_handler(MessageHandler(filters.Regex("^Забронювати вільні години$"), handle_booking))
    application.add_handler(MessageHandler(filters.Regex("^Скасувати заняття$"), handle_cancellation))
    application.add_handler(MessageHandler(filters.Regex("^Переглянути заброньовані заняття$"), handle_view_bookings))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2}$"), handle_day_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}:\d{2}$"), handle_time_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^(1 година|1\.5 години|2 години)$"), handle_duration_selection))
    application.add_handler(MessageHandler(filters.Regex(r"^Назад$"), start_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^\d{2}\.\d{2}\.\d{2} .*"), confirm_cancellation))

    application.run_polling()

if __name__ == '__main__':
    main()
