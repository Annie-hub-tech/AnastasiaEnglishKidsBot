import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "").replace("\n", "").replace("\r", "").strip()

# Список свободных окошек для занятий
AVAILABLE_SLOTS = [
    "Пн 15:00",
    "Пн 17:00",
    "Ср 16:00",
    "Чт 15:30",
    "Пт 17:00",
    "Сб 10:00",
    "Сб 14:00"
]

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
        slots_text = "🗓 <b>Свободные окошки:</b>\n\n"
        for slot in AVAILABLE_SLOTS:
            slots_text += f"• {slot}\n"
        
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

