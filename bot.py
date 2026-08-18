import os
import json
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
import google.auth

TOKEN = os.getenv("BOT_TOKEN", "").replace("\n", "").replace("\r", "").strip()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "").strip()

# Google Sheets API
def get_google_sheets_client():
    """Инициализирует клиент Google Sheets"""
    try:
        creds_dict = None

        # Попытка загрузить из переменной окружения (base64)
        creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "").strip()
        if creds_b64:
            try:
                creds_json = base64.b64decode(creds_b64).decode('utf-8')
                creds_dict = json.loads(creds_json)
            except Exception as e:
                print(f"Error decoding GOOGLE_CREDENTIALS_B64: {e}")
                return None
        else:
            # Попытка загрузить локальный credentials.json
            try:
                with open("credentials.json", "r") as f:
                    creds_dict = json.load(f)
            except FileNotFoundError:
                print("credentials.json not found and GOOGLE_CREDENTIALS_B64 not set")
                return None

        if not creds_dict:
            return None

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        credentials, _ = google.auth.load_credentials_from_dict(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Error initializing Google Sheets: {e}")
        return None

async def get_available_slots():
    """Загружает свободные окошки из Google Sheets"""
    if not SPREADSHEET_ID:
        return None, "⚠️ Google Sheets не настроена (SPREADSHEET_ID не установлен)"

    try:
        client = get_google_sheets_client()
        if not client:
            return None, "⚠️ Не удается подключиться к Google Sheets. Пожалуйста, попробуйте позже."

        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet("Slots")

        # Получаем все данные
        records = worksheet.get_all_records()

        # Фильтруем только доступные слоты (STATUS = "Available")
        available_slots = [
            {"date": r.get("DATE", ""), "time": r.get("TIME", "")}
            for r in records
            if r.get("STATUS", "").strip().lower() == "available"
        ]

        if not available_slots:
            return [], "На данный момент свободных окошек нет. Проверьте позже!"

        return available_slots, None

    except gspread.exceptions.SpreadsheetNotFound:
        return None, "⚠️ Google Sheet не найдена. Проверьте SPREADSHEET_ID."
    except gspread.exceptions.WorksheetNotFound:
        return None, "⚠️ Лист 'Slots' не найден в таблице."
    except Exception as e:
        import traceback
        print(f"Error loading slots: {e}")
        traceback.print_exc()
        return None, "⚠️ Не удалось загрузить расписание. Пожалуйста, попробуйте позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 Отзывы", callback_data="reviews")],
        [InlineKeyboardButton("🗓 Свободные окошки", callback_data="slots")],
        [InlineKeyboardButton("✨ Записаться на урок", callback_data="signup")]
    ]

    text = (
        "Привет! 🌷\n\n"
        "Рада видеть вас здесь.\n\n"
        "Я — помощник Анастасии Александровны, преподавателя английского языка для детей.\n\n"
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
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "reviews":
        await query.message.reply_text("💬 Отзывы родителей:")

        review_files = [
    "review1.jpg",
    "review2.jpg",
    "review3.jpg",
    "review4.jpg",
    "review5.jpg"
]
        for file_name in review_files:
            with open(file_name, "rb") as photo:
                await query.message.reply_photo(photo)
    elif query.data == "slots":
        available_slots, error = await get_available_slots()

        if error:
            await query.message.reply_text(error, parse_mode="HTML")
            return

        if not available_slots:
            await query.message.reply_text("На данный момент свободных окошек нет. Проверьте позже!", parse_mode="HTML")
            return

        slots_text = "🗓 <b>Свободные окошки:</b>\n\n"
        for slot in available_slots:
            date = slot.get("date", "")
            time = slot.get("time", "")
            slots_text += f"• {date} {time}\n"

        slots_keyboard = [
            [InlineKeyboardButton("✨ Записаться на урок", callback_data="signup_from_slots")]
        ]

        await query.message.reply_text(
            slots_text,
            reply_markup=InlineKeyboardMarkup(slots_keyboard),
            parse_mode="HTML"
        )
    elif query.data in ("signup", "signup_from_slots"):
        await query.message.reply_text(
            "✨ <b>Запись на урок</b>\n\n"
            "Пожалуйста, напишите:\n"
            "1. Имя ребенка\n"
            "2. Возраст\n"
            "3. Удобное время\n\n"
            "Анастасия Александровна свяжется с вами в течение 24 часов.",
            parse_mode="HTML"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()

