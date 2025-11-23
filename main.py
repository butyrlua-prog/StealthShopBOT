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

# -------------------- ЛОГИ --------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------- КОНФИГ --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния ConversationHandler
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    MEN_OUTERWEAR_MENU,
    WOMEN_OUTERWEAR_MENU,
    CLOTHES_SIZE,
    SHOES_MENU,
    SHOES_SIZE,
) = range(8)

CLOTHES_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


# -------------------- КЛАВИАТУРЫ --------------------
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
    # XS .. XXL + кнопка назад
    row1 = [KeyboardButton(s) for s in CLOTHES_SIZES[:3]]  # XS S M
    row2 = [KeyboardButton(s) for s in CLOTHES_SIZES[3:]]  # L XL XXL
    keyboard = [
        row1,
        row2,
        [KeyboardButton("Назад к категориям")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    # Размеры 34–46 с половинками
    sizes = []
    current = 34.0
    while current <= 46.0:
        if current.is_integer():
            sizes.append(str(int(current)))
        else:
            sizes.append(f"{current:.1f}")
        current += 0.5

    # раскладываем по 4 в ряд
    rows = []
    row: list[KeyboardButton] = []
    for s in sizes:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton("Назад к обуви")])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# -------------------- ХЕНДЛЕРЫ --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт и главное меню."""
    context.user_data.clear()
    await update.message.reply_text(
        "Добро пожаловать в магазин. Выберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ------- ГЛАВНОЕ МЕНЮ -------
async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Мужская одежда":
        context.user_data["gender"] = "men"
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text == "Женская одежда":
        context.user_data["gender"] = "women"
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
            "Раздел обувь. Выберите категорию:",
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
        "Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ------- МУЖСКАЯ ОДЕЖДА -------
async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите тип:",
            reply_markup=men_outerwear_keyboard(),
        )
        return MEN_OUTERWEAR_MENU

    # Остальные подкатегории пока-заглушки
    if text == "Сумки | Рюкзаки":
        await update.message.reply_text("Мужские сумки и рюкзаки: список товаров появится позже.")
    elif text == "Футболки":
        await update.message.reply_text("Мужские футболки: список товаров появится позже.")
    elif text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: список товаров появится позже.")
    elif text == "Штаны | Шорты":
        await update.message.reply_text("Мужские штаны и шорты: список товаров появится позже.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return MEN_MENU


# ------- ЖЕНСКАЯ ОДЕЖДА -------
async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите тип:",
            reply_markup=women_outerwear_keyboard(),
        )
        return WOMEN_OUTERWEAR_MENU

    if text == "Сумки":
        await update.message.reply_text("Женские сумки: список товаров появится позже.")
    elif text == "Головные уборы":
        await update.message.reply_text("Женские головные уборы: список товаров появится позже.")
    elif text == "Футболки | Топы":
        await update.message.reply_text("Футболки и топы: список товаров появится позже.")
    elif text == "Штаны | Шорты":
        await update.message.reply_text("Женские штаны и шорты: список товаров появится позже.")
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")

    return WOMEN_MENU


# ------- ВЕРХНЯЯ ОДЕЖДА (МУЖ) -------
async def men_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    # сохраним, что человек в верхней одежде, чтобы потом использовать
    context.user_data["section"] = "men_outerwear"
    context.user_data["outer_type"] = text

    if text in [
        "Куртки | Плащи | Ветровки",
        "Худи | Свитшоты | Олимпийки",
        "Бомберы | Свитеры",
    ]:
        await update.message.reply_text(
            "Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return CLOTHES_SIZE

    await update.message.reply_text("Выберите пункт из списка.")
    return MEN_OUTERWEAR_MENU


# ------- ВЕРХНЯЯ ОДЕЖДА (ЖЕН) -------
async def women_outerwear_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    context.user_data["section"] = "women_outerwear"
    context.user_data["outer_type"] = text

    if text in [
        "Куртки",
        "Худи | Свитшоты | Олимпийки",
        "Свитеры | Бомберы",
    ]:
        await update.message.reply_text(
            "Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return CLOTHES_SIZE

    await update.message.reply_text("Выберите пункт из списка.")
    return WOMEN_OUTERWEAR_MENU


# ------- РАЗМЕРЫ ОДЕЖДЫ -------
async def clothes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        # смотрим, в каком разделе человек
        section = context.user_data.get("section")
        gender = context.user_data.get("gender")

        if section in ("men_outerwear",) or gender == "men":
            await update.message.reply_text(
                "Мужская верхняя одежда. Выберите тип:",
                reply_markup=men_outerwear_keyboard(),
            )
            return MEN_OUTERWEAR_MENU
        else:
            await update.message.reply_text(
                "Женская верхняя одежда. Выберите тип:",
                reply_markup=women_outerwear_keyboard(),
            )
            return WOMEN_OUTERWEAR_MENU

    if text in CLOTHES_SIZES:
        # позже здесь будем брать товары из Google Sheets
        await update.message.reply_text(
            f"Вы выбрали размер {text}. Товары этого размера будут показаны здесь позже."
        )
        # остаёмся в выборе размера, чтобы можно было выбрать другой
        return CLOTHES_SIZE

    await update.message.reply_text("Выберите размер с кнопок ниже.")
    return CLOTHES_SIZE


# ------- ОБУВЬ: КАТЕГОРИИ -------
async def shoes_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text("Выберите пункт из списка.")
    return SHOES_MENU


# ------- ОБУВЬ: РАЗМЕРЫ -------
async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к обуви":
        await update.message.reply_text(
            "Раздел обувь. Выберите категорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    # Любой размер, который пришёл с кнопки, принимаем как валидный
    if text.replace(".", "", 1).isdigit():
        cat = context.user_data.get("shoes_category", "Обувь")
        await update.message.reply_text(
            f"{cat}, размер {text}. Товары этого размера будут показаны здесь позже."
        )
        return SHOES_SIZE

    await update.message.reply_text("Выберите размер с кнопок ниже.")
    return SHOES_SIZE


# -------------------- MAIN --------------------
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
            CLOTHES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, clothes_size_router)
            ],
            SHOES_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_menu_router)
            ],
            SHOES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
