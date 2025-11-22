import os
import logging
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

# Логирование (на всякий случай)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Токен берём из переменной окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    MEN_OUTER_MENU,
    WOMEN_OUTER_MENU,
    SHOES_MENU,
    MEN_SIZE_MENU,
    WOMEN_SIZE_MENU,
) = range(8)


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
    keyboard = [
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL"), KeyboardButton("XXL")],
        [KeyboardButton("Назад к подкатегориям")],
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
    # Размеры 34–46 с половинками
    sizes = [
        "34", "34,5", "35", "35,5",
        "36", "36,5", "37", "37,5",
        "38", "38,5", "39", "39,5",
        "40", "40,5", "41", "41,5",
        "42", "42,5", "43", "43,5",
        "44", "44,5", "45", "45,5",
        "46",
    ]
    keyboard = []
    row = []
    for s in sizes:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("Назад к выбору обуви")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------- ОБРАБОТЧИКИ ----------

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
            "Раздел обуви. Сначала выберите категорию:",
            reply_markup=shoes_category_keyboard(),
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


# ----- Мужская одежда -----

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

    if text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: пока без списка товаров.")
        return MEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите подкатегорию:",
            reply_markup=men_outerwear_keyboard(),
        )
        return MEN_OUTER_MENU

    if text in ["Футболки", "Штаны | Шорты"]:
        # Переход в выбор размера одежды
        context.user_data["men_clothes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_SIZE_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return MEN_MENU


async def men_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    outer_cats = [
        "Куртки | Плащи | Ветровки",
        "Худи | Свитшоты | Олимпийки",
        "Бомберы | Свитеры",
    ]

    if text in outer_cats:
        context.user_data["men_clothes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_SIZE_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return MEN_OUTER_MENU


async def men_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к подкатегориям":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    if text in sizes:
        category = context.user_data.get("men_clothes_category", "Категория не выбрана")
        await update.message.reply_text(
            f"{category}, размер {text}: пока без списка товаров."
        )
        return MEN_SIZE_MENU

    await update.message.reply_text(
        "Выберите размер из списка или нажмите 'Назад к подкатегориям'."
    )
    return MEN_SIZE_MENU


# ----- Женская одежда -----

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

    if text == "Головные уборы":
        await update.message.reply_text("Женские головные уборы: пока без списка товаров.")
        return WOMEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите подкатегорию:",
            reply_markup=women_outerwear_keyboard(),
        )
        return WOMEN_OUTER_MENU

    if text in ["Футболки | Топы", "Штаны | Шорты"]:
        context.user_data["women_clothes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_SIZE_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return WOMEN_MENU


async def women_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    outer_cats = [
        "Куртки",
        "Худи | Свитшоты | Олимпийки",
        "Свитеры | Бомберы",
    ]

    if text in outer_cats:
        context.user_data["women_clothes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_SIZE_MENU

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return WOMEN_OUTER_MENU


async def women_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к подкатегориям":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    if text in sizes:
        category = context.user_data.get("women_clothes_category", "Категория не выбрана")
        await update.message.reply_text(
            f"{category}, размер {text}: пока без списка товаров."
        )
        return WOMEN_SIZE_MENU

    await update.message.reply_text(
        "Выберите размер из списка или нажмите 'Назад к подкатегориям'."
    )
    return WOMEN_SIZE_MENU


# ----- Обувь -----

async def shoes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Назад к выбору обуви":
        await update.message.reply_text(
            "Раздел обуви. Выберите категорию:",
            reply_markup=shoes_category_keyboard(),
        )
        # Остаёмся в SHOES_MENU
        return SHOES_MENU

    categories = ["Кроссовки", "Кеды", "Сланцы", "Ботинки"]
    if text in categories:
        context.user_data["shoes_category"] = text
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_MENU

    sizes = [
        "34", "34,5", "35", "35,5",
        "36", "36,5", "37", "37,5",
        "38", "38,5", "39", "39,5",
        "40", "40,5", "41", "41,5",
        "42", "42,5", "43", "43,5",
        "44", "44,5", "45", "45,5",
        "46",
    ]

    if text in sizes:
        cat = context.user_data.get("shoes_category")
        if not cat:
            await update.message.reply_text(
                "Сначала выберите категорию обуви.",
                reply_markup=shoes_category_keyboard(),
            )
            return SHOES_MENU

        await update.message.reply_text(
            f"{cat}, размер {text}: пока без списка товаров."
        )
        return SHOES_MENU

    await update.message.reply_text(
        "Выберите категорию обуви или размер из списка.",
    )
    return SHOES_MENU


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
            MEN_OUTER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outerwear_router)
            ],
            WOMEN_OUTER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outerwear_router)
            ],
            MEN_SIZE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_size_router)
            ],
            WOMEN_SIZE_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_size_router)
            ],
            SHOES_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
