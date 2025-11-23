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

# -----------------------------
# Настройки
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния диалога
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    MEN_OUTER_MENU,
    WOMEN_OUTER_MENU,
    SHOES_CATEGORY,
    SHOES_SIZE,
) = range(7)

# -----------------------------
# Клавиатуры
# -----------------------------


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Мужская одежда"), KeyboardButton("Женская одежда")],
        [KeyboardButton("Аксессуары"), KeyboardButton("Обувь")],
        [KeyboardButton("Распродажа"), KeyboardButton("Моя корзина")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def men_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сумки | Рюкзаки"), KeyboardButton("Верхняя одежда (муж)")],
        [KeyboardButton("Футболки"), KeyboardButton("Головные уборы")],
        [KeyboardButton("Штаны | Шорты")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сумки"), KeyboardButton("Головные уборы (жен)")],
        [KeyboardButton("Футболки | Топы"), KeyboardButton("Верхняя одежда (жен)")],
        [KeyboardButton("Штаны | Шорты")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def men_outerwear_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Куртки | Плащи | Ветровки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Бомберы | Свитеры")],
        [KeyboardButton("Назад к мужской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_outerwear_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Куртки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Свитеры | Бомберы")],
        [KeyboardButton("Назад к женской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clothes_size_keyboard() -> ReplyKeyboardMarkup:
    # Общая размерная сетка для одежды
    keyboard = [
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL")],
        [KeyboardButton("XXL"), KeyboardButton("XXXL")],
        [KeyboardButton("Назад к категориям")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_category_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    # 34–46, с половинками
    row1 = [KeyboardButton(x) for x in ["34", "34.5", "35", "35.5"]]
    row2 = [KeyboardButton(x) for x in ["36", "36.5", "37", "37.5"]]
    row3 = [KeyboardButton(x) for x in ["38", "38.5", "39", "39.5"]]
    row4 = [KeyboardButton(x) for x in ["40", "40.5", "41", "41.5"]]
    row5 = [KeyboardButton(x) for x in ["42", "42.5", "43", "43.5"]]
    row6 = [KeyboardButton(x) for x in ["44", "44.5", "45", "45.5", "46"]]
    back = [KeyboardButton("Назад к категориям обуви")]
    keyboard = [row1, row2, row3, row4, row5, row6, back]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# -----------------------------
# Хэндлеры
# -----------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в StealthShop.\nВыберите раздел:",
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
            "Раздел обуви. Сначала выберите категорию:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY

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


# --- Мужская одежда ---


async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Сумки | Рюкзаки":
        await update.message.reply_text("Мужские сумки и рюкзаки: пока без списка товаров.")
        return MEN_MENU

    if text == "Футболки":
        await update.message.reply_text(
            "Мужские футболки. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_MENU

    if text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: пока без списка товаров.")
        return MEN_MENU

    if text == "Штаны | Шорты":
        await update.message.reply_text(
            "Мужские штаны и шорты. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_MENU

    if text == "Верхняя одежда (муж)":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите тип:",
            reply_markup=men_outerwear_keyboard(),
        )
        return MEN_OUTER_MENU

    if text == "Назад к категориям":
        # после выбора размера
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    await update.message.reply_text("Выберите пункт из меню мужской одежды.")
    return MEN_MENU


async def men_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text in [
        "Куртки | Плащи | Ветровки",
        "Худи | Свитшоты | Олимпийки",
        "Бомберы | Свитеры",
    ]:
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_OUTER_MENU

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите тип:",
            reply_markup=men_outerwear_keyboard(),
        )
        return MEN_OUTER_MENU

    await update.message.reply_text("Выберите пункт из списка.")
    return MEN_OUTER_MENU


# --- Женская одежда ---


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
        return WOMEN_MENU

    if text == "Головные уборы (жен)":
        await update.message.reply_text("Женские головные уборы: пока без списка товаров.")
        return WOMEN_MENU

    if text == "Футболки | Топы":
        await update.message.reply_text(
            "Футболки и топы. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_MENU

    if text == "Штаны | Шорты":
        await update.message.reply_text(
            "Женские штаны и шорты. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_MENU

    if text == "Верхняя одежда (жен)":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите тип:",
            reply_markup=women_outerwear_keyboard(),
        )
        return WOMEN_OUTER_MENU

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    await update.message.reply_text("Выберите пункт из меню женской одежды.")
    return WOMEN_MENU


async def women_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text in [
        "Куртки",
        "Худи | Свитшоты | Олимпийки",
        "Свитеры | Бомберы",
    ]:
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_OUTER_MENU

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите тип:",
            reply_markup=women_outerwear_keyboard(),
        )
        return WOMEN_OUTER_MENU

    await update.message.reply_text("Выберите пункт из списка.")
    return WOMEN_OUTER_MENU


# --- Обувь ---


async def shoes_category_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in ["Кроссовки", "Кеды", "Сланцы", "Ботинки"]:
        context.user_data["shoes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await update.message.reply_text("Выберите категорию обуви из меню.")
    return SHOES_CATEGORY


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям обуви":
        await update.message.reply_text(
            "Выберите категорию обуви:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY

    # сюда придём, когда пользователь выбрал размер
    category = context.user_data.get("shoes_category", "Обувь")
    await update.message.reply_text(
        f"{category}, размер {text}. Здесь позже будем показывать товары из Google Sheets."
    )
    return SHOES_SIZE


# -----------------------------
# MAIN
# -----------------------------


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router)],
            MEN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, men_menu_router)],
            WOMEN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, women_menu_router)],
            MEN_OUTER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outerwear_router)
            ],
            WOMEN_OUTER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outerwear_router)
            ],
            SHOES_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_category_router)
            ],
            SHOES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
