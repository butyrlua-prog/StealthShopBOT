import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Берём токен из переменной окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния для ConversationHandler
MAIN_MENU, MEN_MENU, WOMEN_MENU, SHOES_MENU, SHOES_SIZES = range(5)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Мужская одежда"), KeyboardButton("Женская одежда")],
        [KeyboardButton("Аксессуары"), KeyboardButton("Обувь")],
        [KeyboardButton("Распродажа"), KeyboardButton("Моя корзина")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def men_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сумки | Рюкзаки"), KeyboardButton("Верхняя одежда")],
        [KeyboardButton("Футболки"), KeyboardButton("Головные уборы")],
        [KeyboardButton("Штаны | Шорты")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сумки"), KeyboardButton("Головные уборы")],
        [KeyboardButton("Футболки | Топы"), KeyboardButton("Верхняя одежда")],
        [KeyboardButton("Штаны | Шорты")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сланцы")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoe_sizes_keyboard() -> ReplyKeyboardMarkup:
    # Размеры от 34 до 46 включительно
    sizes = [str(i) for i in range(34, 47)]
    # Разбиваем по рядам, по 4 кнопки в ряд (чтоб не было простыни в один ряд)
    rows = [sizes[i:i + 4] for i in range(0, len(sizes), 4)]
    keyboard = [[KeyboardButton(size) for size in row] for row in rows]
    # Добавляем кнопку "Назад к категориям обуви"
    keyboard.append([KeyboardButton("Назад к категориям обуви")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Мужская одежда":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text == "Женская одежда":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров пока в разработке.")
        return MAIN_MENU

    if text == "Обувь":
        await update.message.reply_text(
            "Раздел обуви. Выберите категорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        await update.message.reply_text("Корзина пока пустая.")
        return MAIN_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Сумки | Рюкзаки":
        await update.message.reply_text("Сумки и рюкзаки: пока без списка товаров.")
    elif text == "Верхняя одежда":
        await update.message.reply_text("Мужская верхняя одежда: пока без списка товаров.")
    elif text == "Футболки":
        await update.message.reply_text("Мужские футболки: пока без списка товаров.")
    elif text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: пока без списка товаров.")
    elif text == "Штаны | Шорты":
        await update.message.reply_text("Мужские штаны и шорты: пока без списка товаров.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return MEN_MENU


async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Сумки":
        await update.message.reply_text("Женские сумки: пока без списка товаров.")
    elif text == "Головные уборы":
        await update.message.reply_text("Женские головные уборы: пока без списка товаров.")
    elif text == "Футболки | Топы":
        await update.message.reply_text("Футболки и топы: пока без списка товаров.")
    elif text == "Верхняя одежда":
        await update.message.reply_text("Женская верхняя одежда: пока без списка товаров.")
    elif text == "Штаны | Шорты":
        await update.message.reply_text("Женские штаны и шорты: пока без списка товаров.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return WOMEN_MENU


async def shoes_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Сланцы":
        await update.message.reply_text(
            "Сланцы. Выберите размер:",
            reply_markup=shoe_sizes_keyboard(),
        )
        return SHOES_SIZES

    await update.message.reply_text("Выберите категорию обуви из списка.")
    return SHOES_MENU


async def shoes_sizes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям обуви":
        await update.message.reply_text(
            "Раздел обуви. Выберите категорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    # Проверяем, что это один из размеров 34–46
    valid_sizes = [str(i) for i in range(34, 47)]
    if text in valid_sizes:
        await update.message.reply_text(
            f"Сланцы, размер {text}: пока без списка товаров."
        )
    else:
        await update.message.reply_text("Выберите размер из списка.")

    return SHOES_SIZES


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router)
            ],
            MEN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_menu_router)
            ],
            WOMEN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_menu_router)
            ],
            SHOES_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_menu_router)
            ],
            SHOES_SIZES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_sizes_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
