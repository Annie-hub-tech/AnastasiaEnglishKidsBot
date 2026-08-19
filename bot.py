import os
import json
import base64
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from ai_assistant import ask_ai

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


TOKEN = os.getenv("BOT_TOKEN", "").replace("\n", "").replace("\r", "").strip()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
if ADMIN_ID and ADMIN_ID.isdigit():
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = None

ASKING_NAME, ASKING_AGE, ASKING_PARENT, CONFIRMING = range(4)


ABOUT_TEXT = (
    "👩‍🏫 Обо мне кратко\n\n"
    "Меня зовут Анастасия Александровна. Я преподаватель английского языка "
    "с высшим филологическим образованием и большим опытом работы с детьми.\n\n"
    "В своей работе я сочетаю системный подход, понятное объяснение материала "
    "и комфортную атмосферу для ребёнка.\n\n"
    "✅ Высшее филологическое образование\n"
    "✅ Опыт работы устным переводчиком\n"
    "✅ Более 16 лет преподавания детям\n"
    "✅ Регулярное участие в профессиональных конференциях по лингвистике "
    "и обучению детей\n\n"
    "Мои ученики не просто улучшают оценки — они начинают лучше понимать английский, "
    "увереннее говорить, перестают бояться ошибок и постепенно чувствуют себя "
    "свободнее в языке.\n\n"
    "Для меня особенно важно видеть реальный прогресс ребёнка и выстраивать обучение "
    "так, чтобы занятия давали результат без постоянного стресса и давления 🌷\n\n"
    "За годы работы десятки учеников добились заметных успехов, а положительные отзывы "
    "родителей стали для меня лучшим подтверждением качества моей работы."
)


def format_russian_date(date_string: str, short_weekday: bool = False):
    """Format YYYY-MM-DD as a Russian date without using the system locale."""
    try:
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
    except (TypeError, ValueError):
        return date_string

    short_day_of_week = {
        0: "Пн",
        1: "Вт",
        2: "Ср",
        3: "Чт",
        4: "Пт",
        5: "Сб",
        6: "Вс",
    }
    full_day_of_week = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }

    weekday_key = parsed_date.weekday()
    weekday_name = (
        short_day_of_week[weekday_key]
        if short_weekday
        else full_day_of_week[weekday_key]
    )

    return f"{weekday_name}, {parsed_date.day} {months[parsed_date.month]}"


# =========================
# GOOGLE SHEETS
# =========================

def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "").strip()

    if creds_b64:
        creds_json = base64.b64decode(creds_b64).decode("utf-8")
        creds_info = json.loads(creds_json)

        credentials = Credentials.from_service_account_info(
            creds_info,
            scopes=scopes,
        )
    else:
        with open("credentials.json", "r", encoding="utf-8") as file:
            creds_info = json.load(file)

        credentials = Credentials.from_service_account_info(
            creds_info,
            scopes=scopes,
        )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet("Slots")


def get_available_slots():
    try:
        worksheet = get_google_sheet()
        records = worksheet.get_all_records()

        slots = []

        for row in records:
            status = str(row.get("STATUS", "")).strip().lower()

            if status == "available":
                date_value = str(row.get("DATE", "")).strip()
                time_value = str(row.get("TIME", "")).strip()

                if date_value and time_value:
                    slots.append(
                        {
                            "date": date_value,
                            "time": time_value,
                        }
                    )

        return slots

    except Exception as error:
        print("Error loading slots:", type(error).__name__)
        return None


def find_slot_row(worksheet, date_value, time_value):
    records = worksheet.get_all_records()

    for row_number, row in enumerate(records, start=2):
        row_date = str(row.get("DATE", "")).strip()
        row_time = str(row.get("TIME", "")).strip()

        if row_date == date_value and row_time == time_value:
            return row_number

    return None


def save_booking(
    date_value,
    time_value,
    student_name,
    age,
    parent_name,
    telegram_username,
    telegram_user_id,
):
    try:
        worksheet = get_google_sheet()

        row_number = find_slot_row(
            worksheet,
            date_value,
            time_value,
        )

        if row_number is None:
            return "not_found"

        # Ещё раз проверяем статус непосредственно перед записью
        current_status = str(
            worksheet.cell(row_number, 3).value or ""
        ).strip().lower()

        if current_status != "available":
            return "slot_taken"

        booked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        worksheet.update(
            range_name=f"C{row_number}:I{row_number}",
            values=[
                [
                    "Booked",
                    student_name,
                    age,
                    parent_name,
                    telegram_username or "",
                    telegram_user_id,
                    booked_at,
                ]
            ],
        )

        return "success"

    except Exception as error:
        print("Error saving booking:", type(error).__name__)
        return "error"


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("👩‍🏫 Обо мне кратко", callback_data="about")],
        [InlineKeyboardButton("🤖 Задать вопрос", callback_data="chat")],
        [InlineKeyboardButton("💬 Отзывы", callback_data="reviews")],
        [InlineKeyboardButton("🗓 Свободные окошки", callback_data="slots")],
        [InlineKeyboardButton("✨ Записаться на урок", callback_data="signup")],
    ]
    text = (
        "Привет! 🌷\n\n"
        "Рада видеть вас здесь.\n\n"
        "Я — помощник Анастасии Александровны, "
        "преподавателя английского языка для детей.\n\n"
        "Здесь можно спокойно познакомиться с Анастасией Александровной, "
        "почитать отзывы родителей, посмотреть свободные окошки "
        "и выбрать удобное время для занятия.\n\n"
        "Анастасия Александровна помогает детям учить английский "
        "без страха ошибок, с интересом и в комфортной атмосфере.\n\n"
        "Она работает с дошкольниками 6–7 лет и школьниками 1–11 классов, "
        "индивидуально, в мини-группах и онлайн.\n\n"
        "Выберите, что хотите посмотреть 👇"
    )

    with open("welcome.png", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT)


# =========================
# ОТЗЫВЫ И СЛОТЫ
# =========================

async def send_slots_message(query):
    slots = get_available_slots()

    if slots is None:
        await query.message.reply_text(
            "⚠️ Не удалось загрузить расписание. "
            "Пожалуйста, попробуйте немного позже."
        )
        return

    if not slots:
        await query.message.reply_text(
            "🌷 Сейчас свободных окошек нет. "
            "Пожалуйста, загляните позже."
        )
        return

    keyboard = []

    for slot in slots:
        date_value = slot["date"]
        time_value = slot["time"]

        formatted_date = format_russian_date(date_value, short_weekday=True)

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{formatted_date} · {time_value}",
                    callback_data=f"book_slot_{date_value}_{time_value}",
                )
            ]
        )

    await query.message.reply_text(
        "🗓 Выберите удобное окошко:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_chat(query, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_mode"] = True
    print("AI chat mode enabled")
    await query.message.reply_text(
        "Здравствуйте! 🌷\n"
        "Я личный AI-помощник Анастасии Александровны.\n"
        "Я могу ответить на вопросы о занятиях, стоимости, расписании, "
        "формате обучения и подходе к занятиям.\n\n"
        "Задайте Ваш вопрос, и я постараюсь помочь."
    )


async def handle_chat_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get("chat_mode"):
        return

    question = update.message.text.strip()
    print(f"AI question received: {question}")

    if not question:
        await update.message.reply_text(
            "Пожалуйста, напишите Ваш вопрос текстом."
        )
        return

    await update.message.reply_text("Минутку, я готовлю ответ 🌷")

    try:
        print("Calling Kie.ai")
        answer = await ask_ai(question)
    except Exception as error:
        print(
            "Error asking AI:",
            type(error).__name__,
            str(error),
        )
        await update.message.reply_text(
            "Не удалось получить ответ. Пожалуйста, попробуйте немного позже "
            "или напишите Анастасии Александровне напрямую."
        )
        return

    print("AI response generated")
    await update.message.reply_text(answer)


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "about":
        await query.message.reply_text(ABOUT_TEXT)

    elif query.data == "reviews":
        await query.message.reply_text("💬 Отзывы родителей:")

        review_files = [
            "review1.jpg",
            "review2.jpg",
            "review3.jpg",
            "review4.jpg",
            "review5.jpg",
        ]

        for file_name in review_files:
            with open(file_name, "rb") as photo:
                await query.message.reply_photo(photo)

    elif query.data == "slots":
        await send_slots_message(query)

    elif query.data == "chat":
        await handle_chat(query, context)

    elif query.data == "signup":
        await query.message.reply_text(
            "✨ Выберите удобное свободное время:"
        )
        await send_slots_message(query)


# =========================
# ЗАПИСЬ НА УРОК
# =========================

def cancel_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="cancel_booking",
                )
            ]
        ]
    )


async def handle_slot_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    slot_data = query.data.removeprefix("book_slot_")

    try:
        date_value, time_value = slot_data.split("_", 1)
    except ValueError:
        await query.message.reply_text(
            "Не удалось определить выбранное время."
        )
        return ConversationHandler.END

    context.user_data.clear()

    context.user_data["selected_date"] = date_value
    context.user_data["selected_time"] = time_value

    user = update.effective_user

    context.user_data["telegram_user_id"] = user.id
    context.user_data["telegram_username"] = user.username or ""

    await query.message.reply_text(
        f"✨ Вы выбрали:\n"
        f"📅 {format_russian_date(date_value)}\n"
        f"🕒 {time_value}\n\n"
        "Как зовут ребёнка?",
        reply_markup=cancel_keyboard(),
    )

    return ASKING_NAME


async def ask_age(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    student_name = update.message.text.strip()

    if not student_name:
        await update.message.reply_text(
            "Пожалуйста, напишите имя ребёнка.",
            reply_markup=cancel_keyboard(),
        )
        return ASKING_NAME

    context.user_data["student_name"] = student_name

    await update.message.reply_text(
        "Сколько лет ребёнку?",
        reply_markup=cancel_keyboard(),
    )

    return ASKING_AGE


async def ask_parent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    age_text = update.message.text.strip()

    if not age_text.isdigit():
        await update.message.reply_text(
            "Напишите возраст цифрами, например: 8",
            reply_markup=cancel_keyboard(),
        )
        return ASKING_AGE

    age = int(age_text)

    if age < 3 or age > 18:
        await update.message.reply_text(
            "Проверьте возраст ребёнка и введите его ещё раз.",
            reply_markup=cancel_keyboard(),
        )
        return ASKING_AGE

    context.user_data["age"] = age

    await update.message.reply_text(
        "Как зовут родителя?",
        reply_markup=cancel_keyboard(),
    )

    return ASKING_PARENT


async def confirm_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    parent_name = update.message.text.strip()

    if not parent_name:
        await update.message.reply_text(
            "Пожалуйста, напишите имя родителя.",
            reply_markup=cancel_keyboard(),
        )
        return ASKING_PARENT

    context.user_data["parent_name"] = parent_name

    date_value = context.user_data["selected_date"]
    time_value = context.user_data["selected_time"]
    student_name = context.user_data["student_name"]
    age = context.user_data["age"]

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Да, записаться",
                callback_data="confirm_booking",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="cancel_booking",
            )
        ],
    ]

    await update.message.reply_text(
        "Проверьте данные 🌷\n\n"
        f"📅 {format_russian_date(date_value)}\n"
        f"🕒 Время: {time_value}\n"
        f"👧 Ребёнок: {student_name}\n"
        f"🎂 Возраст: {age}\n"
        f"👤 Родитель: {parent_name}\n\n"
        "Всё правильно?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CONFIRMING


async def process_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    required_keys = [
        "selected_date",
        "selected_time",
        "student_name",
        "age",
        "parent_name",
        "telegram_user_id",
    ]

    if not all(key in context.user_data for key in required_keys):
        await query.message.reply_text(
            "Данные записи потерялись. "
            "Пожалуйста, выберите время ещё раз."
        )
        context.user_data.clear()
        return ConversationHandler.END

    result = save_booking(
        date_value=context.user_data["selected_date"],
        time_value=context.user_data["selected_time"],
        student_name=context.user_data["student_name"],
        age=context.user_data["age"],
        parent_name=context.user_data["parent_name"],
        telegram_username=context.user_data.get(
            "telegram_username",
            "",
        ),
        telegram_user_id=context.user_data["telegram_user_id"],
    )

    date_value = context.user_data["selected_date"]
    time_value = context.user_data["selected_time"]

    if result == "success":
        await query.message.reply_text(
            "✅ Запись подтверждена!\n\n"
            f"📅 {format_russian_date(date_value)}\n"
            f"🕒 {time_value}\n\n"
            "Анастасия Александровна свяжется с вами 🌷"
        )

        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        "✅ Новая запись на урок\n\n"
                        f"🗓 Дата: {date_value}\n"
                        f"🕒 Время: {time_value}\n"
                        f"👧 Ребёнок: {context.user_data['student_name']}\n"
                        f"🎂 Возраст: {context.user_data['age']}\n"
                        f"👤 Родитель: {context.user_data['parent_name']}\n"
                        f"@{context.user_data.get('telegram_username', '') or 'unknown'}\n"
                        f"ID: {context.user_data['telegram_user_id']}"
                    ),
                )
            except Exception:
                pass

    elif result == "slot_taken":
        await query.message.reply_text(
            "🙏 Это окошко уже занято.\n\n"
            "Нажмите «Свободные окошки» "
            "и выберите другое время."
        )

    elif result == "not_found":
        await query.message.reply_text(
            "Не удалось найти это время в расписании. "
            "Пожалуйста, выберите другое."
        )

    else:
        await query.message.reply_text(
            "⚠️ Не удалось сохранить запись. "
            "Пожалуйста, попробуйте немного позже."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query:
        await query.answer()
        await query.message.reply_text("Запись отменена 🌷")

    context.user_data.clear()
    return ConversationHandler.END


async def restart_during_booking(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END


# =========================
# ЗАПУСК
# =========================

async def setup_bot_commands(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Главное меню"),
            BotCommand("about", "Обо мне кратко"),
        ]
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    if not SPREADSHEET_ID:
        print("Warning: SPREADSHEET_ID is not set")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(setup_bot_commands)
        .build()
    )

    booking_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handle_slot_selection,
                pattern=r"^book_slot_",
            )
        ],
        states={
            ASKING_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    ask_age,
                ),
                CallbackQueryHandler(
                    cancel_booking,
                    pattern=r"^cancel_booking$",
                ),
            ],
            ASKING_AGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    ask_parent,
                ),
                CallbackQueryHandler(
                    cancel_booking,
                    pattern=r"^cancel_booking$",
                ),
            ],
            ASKING_PARENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    confirm_booking,
                ),
                CallbackQueryHandler(
                    cancel_booking,
                    pattern=r"^cancel_booking$",
                ),
            ],
            CONFIRMING: [
                CallbackQueryHandler(
                    process_booking,
                    pattern=r"^confirm_booking$",
                ),
                CallbackQueryHandler(
                    cancel_booking,
                    pattern=r"^cancel_booking$",
                ),
            ],
        },
        fallbacks=[
            CommandHandler(
                "start",
                restart_during_booking,
            ),
            CallbackQueryHandler(
                cancel_booking,
                pattern=r"^cancel_booking$",
            ),
        ],
        conversation_timeout=1800,
    )

    # ConversationHandler ставим первым:
    # во время записи он должен перехватывать свои события.
    app.add_handler(booking_handler)

    # Обычный /start, когда пользователь не находится в сценарии записи.
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_chat_message,
        )
    )

    # Остальные кнопки меню.
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
