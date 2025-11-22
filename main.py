import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


# ------------------ ГЛАВНОЕ МЕНЮ ------------------

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("👕 Мужская одежда", callback_data="MEN")],
        [InlineKeyboardButton("👗 Женская одежда", callback_data="WOMEN")],
        [InlineKeyboardButton("🎒 Аксессуары", callback_data="ACCESSORIES")],
        [InlineKeyboardButton("👟 Обувь", callback_data="SHOES")],
        [InlineKeyboardButton("🔥 Распродажа", callback_data="SALE")],
        [InlineKeyboardButton("🧺 Моя корзина", callback_data="CART")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин!\nВыберите категорию 👇",
        reply_markup=main_menu_keyboard()
    )


# ------------------ ОБРАБОТКА КНОПОК ------------------

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "MEN":
        await query.edit_message_text(
            "Вы выбрали: Мужская одежда 👕\n(подкатегории добавим следующим шагом)",
            reply_markup=main_menu_keyboard()
        )

    elif data == "WOMEN":
        await query.edit_message_text(
            "Вы выбрали: Женская одежда 👗\n(подкатегории добавим следующим шагом)",
            reply_markup=main_menu_keyboard()
        )

    elif data == "ACCESSORIES":
        await query.edit_message_text(
            "Вы выбрали: Аксессуары 🎒\n(подкатегории добавим следующим шагом)",
            reply_markup=main_menu_keyboard()
        )

    elif data == "SHOES":
        await query.edit_message_text(
            "Вы выбрали: Обувь 👟\n(подкатегории добавим следующим шагом)",
            reply_markup=main_menu_keyboard()
        )

    elif data == "SALE":
        await query.edit_message_text(
            "Раздел: 🔥 Распродажа\n(добавим позже)",
            reply_markup=main_menu_keyboard()
        )

    elif data == "CART":
        await query.edit_message_text(
            "🧺 Ваша корзина пуста.\n(Функционал добавим позже)",
            reply_markup=main_menu_keyboard()
        )


# ------------------ ЗАПУСК ------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.run_polling()


if __name__ == "__main__":
    main()
