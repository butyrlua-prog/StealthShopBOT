import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Наши категории (кнопки)
CATEGORIES = [
    ["Мужская одежда", "Женская одежда"],
    ["Обувь", "Аксессуары"],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        CATEGORIES,
        resize_keyboard=True,
        one_time_keyboard=False,  # кнопки будут оставаться
    )
    await update.message.reply_text(
        "Привет! Это магазин.\nВыбери категорию ниже 👇",
        reply_markup=keyboard,
    )

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Плоский список всех названий категорий
    all_categories = [name for row in CATEGORIES for name in row]

    if text in all_categories:
        await update.message.reply_text(
            f"Ты выбрал категорию: *{text}*\n"
            "Пока здесь просто заглушка, дальше добавим список товаров 😉",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "Пока я понимаю только кнопки категорий снизу.\n"
            "Нажми на одну из них 👇"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category))
    app.run_polling()

if __name__ == "__main__":
    main()
