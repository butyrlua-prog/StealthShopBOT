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
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_CATEGORY_MENU,
    SHOES_SIZE_MENU,
    MEN_OUTERWEAR_MENU,
    WOMEN_OUTERWEAR_MENU,
) = range(7)


# ---------- КЛАВИАТУРЫ ----------

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


def shoes_category_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    # Размеры 34–46 с половинками: 34, 34,5, 35, 35,5, ..., 45,5, 46
    sizes = [
        "34", "34,5", "35", "35,5",
        "36", "36,5", "37", "37,5",
        "38", "38,5", "39", "39,5",
        "40", "40,5", "41", "41,5",
        "42", "42,5", "43", "43,5",
        "44", "44,5", "45", "45,5",
        "46",
    ]

    # Разобьём по 4 в строке
    keyboard_rows = []
    row = []
    for s in sizes:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            keyboard_rows.append(row)
            row = []
    if row:
        keyboard_rows.append(row)

    # Кнопка назад
    keyboard_rows.append([KeyboardButton("Назад к категориям обуви")])

    return ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True)


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


# ---------- ХЕНДЛЕРЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт и показ главного меню."""
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем нажатия в главном меню."""
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
        return SHOES_CATEGORY_MENU

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


# ----- МУЖСКОЕ МЕНЮ -----

async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подкатегории мужской одежды."""
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
        await update.message.reply_text("Мужские футболки: пока без списка товаров.")
        return MEN_MENU

    if text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: пока без списка товаров.")
        return MEN_MENU

    if text == "Штаны | Шорты":
        await update.message.reply_text("Мужские штаны и шорты: пока без списка товаров.")
        return MEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите подкатегорию:",
            reply_markup=men_outerwear_keyboard(),
        )
        return MEN_OUTERWEAR_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return MEN_MENU


async def men_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подкатегории мужской верхней одежды."""
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text == "Куртки | Плащи | Ветровки":
        await update.message.reply_text("Мужские куртки, плащи и ветровки: пока без списка товаров.")
    elif text == "Худи | Свитшоты | Олимпийки":
        await update.message.reply_text("Мужские худи, свитшоты и олимпийки: пока без списка товаров.")
    elif text == "Бомберы | Свитеры":
        await update.message.reply_text("Мужские бомберы и свитеры: пока без списка товаров.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return MEN_OUTERWEAR_MENU


# ----- ЖЕНСКОЕ МЕНЮ -----

async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подкатегории женской одежды."""
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

    if text == "Головные уборы":
        await update.message.reply_text("Женские головные уборы: пока без списка товаров.")
        return WOMEN_MENU

    if text == "Футболки | Топы":
        await update.message.reply_text("Женские футболки и топы: пока без списка товаров.")
        return WOMEN_MENU

    if text == "Штаны | Шорты":
        await update.message.reply_text("Женские штаны и шорты: пока без списка товаров.")
        return WOMEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите подкатегорию:",
            reply_markup=women_outerwear_keyboard(),
        )
        return WOMEN_OUTERWEAR_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return WOMEN_MENU


async def women_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подкатегории женской верхней одежды."""
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text == "Куртки":
        await update.message.reply_text("Женские куртки: пока без списка товаров.")
    elif text == "Худи | Свитшоты | Олимпийки":
        await update.message.reply_text("Женские худи, свитшоты и олимпийки: пока без списка товаров.")
    elif text == "Свитеры | Бомберы":
        await update.message.reply_text("Женские свитеры и бомберы: пока без списка товаров.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return WOMEN_OUTERWEAR_MENU


# ----- ОБУВЬ -----

async def shoes_category_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор категории обуви: кроссовки, кеды, сланцы, ботинки."""
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in ["Кроссовки", "Кеды", "Сланцы", "Ботинки"]:
        # Запоминаем выбранную категорию обуви
        context.user_data["shoe_category"] = text
        await update.message.reply_text(
            f"{text}. Теперь выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE_MENU

    await update.message.reply_text(
        "Выберите категорию обуви из списка.",
        reply_markup=shoes_category_keyboard(),
    )
    return SHOES_CATEGORY_MENU


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор размера обуви."""
    text = update.message.text

    if text == "Назад к категориям обуви":
        await update.message.reply_text(
            "Раздел обуви. Выберите категорию:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY_MENU

    allowed_sizes = {
        "34", "34,5", "35", "35,5",
        "36", "36,5", "37", "37,5",
        "38", "38,5", "39", "39,5",
        "40", "40,5", "41", "41,5",
        "42", "42,5", "43", "43,5",
        "44", "44,5", "45", "45,5",
        "46",
    }

    if text in allowed_sizes:
        category = context.user_data.get("shoe_category", "Обувь")
        await update.message.reply_text(
            f"{category}, размер {text}: пока без списка товаров."
        )
        # Остаёмся в выборе размера — клиент может выбрать другой
        return SHOES_SIZE_MENU

    await update.message.reply_text("Выберите размер из списка.")
    return SHOES_SIZE_MENU


# ---------- MAIN ----------

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
            MEN_OUTERWEAR_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outerwear_router)
            ],
            WOMEN_OUTERWEAR_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outerwear_router)
            ],
            SHOES_CATEGORY_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_category_router)
            ],
            SHOES_SIZE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
    main()
