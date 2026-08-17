import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
👋 Привет!

Я персональный ассистент Анастасии Александровны.

Анастасия Александровна — преподаватель английского языка для детей.

Она помогает дошкольникам и школьникам изучать английский легко,
интересно и с уверенностью.

На занятиях:
✨ развиваем разговорную речь
✨ изучаем грамматику и лексику
✨ учимся понимать английскую речь
✨ занимаемся в комфортной атмосфере
"""

    keyboard = [
        [
            InlineKeyboardButton(
                "⭐ Отзывы",
                callback_data="reviews"
            )
        ],
        [
            InlineKeyboardButton(
                "📅 Свободные окна",
                callback_data="slots"
            )
        ],
        [
            InlineKeyboardButton(
                "🎓 Записаться на урок",
                callback_data="signup"
            )
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "reviews":
        await query.message.reply_text(
            "⭐ Здесь скоро появятся отзывы учеников."
        )

    elif query.data == "slots":
        await query.message.reply_text(
            "📅 Здесь будут свободные окна для занятий."
        )

    elif query.data == "signup":
        await query.message.reply_text(
            "🎓 Для записи напишите мне:\n\n"
            "Имя ребёнка\n"
            "Возраст\n"
            "Удобное время"
        )


def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()
