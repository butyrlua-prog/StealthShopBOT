import logging
import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# --- Состояния диалога ---
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    MEN_OUTER_MENU,
    WOMEN_OUTER_MENU,
    SHOES_MENU,
    SIZE_CLOTHES,
    SIZE_SHOES,
) = range(8)

# --- Константы для кодов (то, что пойдёт в таблицу потом) ---

CLOTHES_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

SHOES_SIZES = [
    "34", "34,5", "35", "35,5", "36", "36,5",
    "37", "37,5", "38", "38,5", "39", "39,5",
    "40", "40,5", "41", "41,5", "42", "42,5",
    "43", "43,5", "44", "44,5", "45", "45,5",
    "46",
]

MEN_LEAF_SUBCATS = {
    "Футболки": "men_tshirts",
    "Штаны | Шорты": "men_pants_shorts",
    "Куртки | Плащи | Ветровки": "men_outer_jackets",
    "Худи | Свитшоты | Олимпийки": "men_outer_hoodies",
    "Бомберы | Свитеры": "men_outer_bombers_sweaters",
    "Сумки | Рюкзаки": "men_bags_backpacks",
    "Головные уборы": "men_headwear",
}

WOMEN_LEAF_SUBCATS = {
    "Футболки | Топы": "women_tshirts_tops",
    "Штаны | Шорты": "women_pants_shorts",
    "Куртки": "women_outer_jackets",
    "Худи | Свитшоты | Олимпийки": "women_outer_hoodies",
    "Свитеры | Бомберы": "women_outer_sweaters_bombers",
    "Сумки": "women_bags",
    "Головные уборы": "women_headwear",
}

SHOES_SUBCATS = {
    "Кроссовки": "shoes_sneakers",
    "Кеды": "shoes_keds",
    "Сланцы": "shoes_slippers",
    "Ботинки": "shoes_boots",
}


# --- Клавиатуры ---

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


def men_outer_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Куртки | Плащи | Ветровки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Бомберы | Свитеры")],
        [KeyboardButton("Назад к мужской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_outer_menu_keyboard() -> ReplyKeyboardMarkup:
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
    rows = []
    row: list[KeyboardButton] = []
    for size in SHOES_SIZES:
        row.append(KeyboardButton(size))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# --- Вспомогательные функции ---

def reset_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()


def set_basic_context(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    gender: str | None,
    main_category: str | None,
) -> None:
    if gender is not None:
        context.user_data["gender"] = gender
    if main_category is not None:
        context.user_data["main_category"] = main_category


def set_subcategory(
    context: ContextTypes.DEFAULT_TYPE,
    code: str,
    label: str,
) -> None:
    context.user_data["subcategory"] = code
    context.user_data["subcategory_label"] = label


def set_size(
    context: ContextTypes.DEFAULT_TYPE,
    size_group: str,
    size_value: str,
) -> None:
    context.user_data["size_group"] = size_group
    context.user_data["size"] = size_value


def build_selection_summary(context: ContextTypes.DEFAULT_TYPE) -> str:
    gender = context.user_data.get("gender")
    main_category = context.user_data.get("main_category")
    sub_label = context.user_data.get("subcategory_label")
    size_group = context.user_data.get("size_group")
    size = context.user_data.get("size")

    parts: list[str] = []

    if gender == "men":
        parts.append("Мужская одежда")
    elif gender == "women":
        parts.append("Женская одежда")
    elif gender == "unisex":
        parts.append("Обувь")

    if main_category == "clothes":
        parts.append("одежда")
    elif main_category == "shoes":
        parts.append("обувь")

    if sub_label:
        parts.append(sub_label)

    if size_group and size:
        parts.append(f"размер {size}")

    if not parts:
        return "Выбор сохранён."

    return "Вы выбрали: " + " → ".join(parts) + ".\n" \
        "Позже здесь будут показываться товары из каталога."


# --- Хэндлеры ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user_data(context)
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Мужская одежда":
        set_basic_context(context, gender="men", main_category="clothes")
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text == "Женская одежда":
        set_basic_context(context, gender="women", main_category="clothes")
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text == "Обувь":
        # Обувь общая, без деления по полу
        set_basic_context(context, gender="unisex", main_category="shoes")
        await update.message.reply_text(
            "Раздел обуви. Выберите тип:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text == "Аксессуары":
        set_basic_context(context, gender=None, main_category="accessories")
        await update.message.reply_text(
            "Раздел аксессуаров пока в разработке."
        )
        return MAIN_MENU

    if text == "Распродажа":
        set_basic_context(context, gender=None, main_category="sale")
        await update.message.reply_text(
            "Раздел распродажи пока в разработке."
        )
        return MAIN_MENU

    if text == "Моя корзина":
        set_basic_context(context, gender=None, main_category="cart")
        await update.message.reply_text(
            "Корзина пока пустая."
        )
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

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите тип:",
            reply_markup=men_outer_menu_keyboard(),
        )
        return MEN_OUTER_MENU

    if text in ("Футболки", "Штаны | Шорты"):
        code = MEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="men", main_category="clothes")
        set_subcategory(context, code, text)

        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return SIZE_CLOTHES

    if text in ("Сумки | Рюкзаки", "Головные уборы"):
        code = MEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="men", main_category="clothes")
        set_subcategory(context, code, text)
        await update.message.reply_text(
            "Товары этого раздела будут добавлены позже."
        )
        return MEN_MENU

    await update.message.reply_text(
        "Выберите подкатегорию из списка.",
        reply_markup=men_menu_keyboard(),
    )
    return MEN_MENU


async def men_outer_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    if text in (
        "Куртки | Плащи | Ветровки",
        "Худи | Свитшоты | Олимпийки",
        "Бомберы | Свитеры",
    ):
        code = MEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="men", main_category="clothes")
        set_subcategory(context, code, text)

        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return SIZE_CLOTHES

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=men_outer_menu_keyboard(),
    )
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

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите тип:",
            reply_markup=women_outer_menu_keyboard(),
        )
        return WOMEN_OUTER_MENU

    if text in ("Футболки | Топы", "Штаны | Шорты"):
        code = WOMEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="women", main_category="clothes")
        set_subcategory(context, code, text)

        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return SIZE_CLOTHES

    if text in ("Сумки", "Головные уборы"):
        code = WOMEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="women", main_category="clothes")
        set_subcategory(context, code, text)
        await update.message.reply_text(
            "Товары этого раздела будут добавлены позже."
        )
        return WOMEN_MENU

    await update.message.reply_text(
        "Выберите подкатегорию из списка.",
        reply_markup=women_menu_keyboard(),
    )
    return WOMEN_MENU


async def women_outer_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text in ("Куртки", "Худи | Свитшоты | Олимпийки", "Свитеры | Бомберы"):
        code = WOMEN_LEAF_SUBCATS[text]
        set_basic_context(context, gender="women", main_category="clothes")
        set_subcategory(context, code, text)

        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return SIZE_CLOTHES

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=women_outer_menu_keyboard(),
    )
    return WOMEN_OUTER_MENU


# --- Размерная сетка одежды ---

async def size_clothes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        gender = context.user_data.get("gender")
        if gender == "men":
            await update.message.reply_text(
                "Мужская одежда. Выберите подкатегорию:",
                reply_markup=men_menu_keyboard(),
            )
            return MEN_MENU
        elif gender == "women":
            await update.message.reply_text(
                "Женская одежда. Выберите подкатегорию:",
                reply_markup=women_menu_keyboard(),
            )
            return WOMEN_MENU
        else:
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=main_menu_keyboard(),
            )
            return MAIN_MENU

    if text in CLOTHES_SIZES:
        set_size(context, "clothes", text)
        summary = build_selection_summary(context)
        await update.message.reply_text(summary)

        # Возвращаем пользователя к выбору подкатегории одежды
        gender = context.user_data.get("gender")
        if gender == "men":
            await update.message.reply_text(
                "Мужская одежда. Выберите подкатегорию:",
                reply_markup=men_menu_keyboard(),
            )
            return MEN_MENU
        elif gender == "women":
            await update.message.reply_text(
                "Женская одежда. Выберите подкатегорию:",
                reply_markup=women_menu_keyboard(),
            )
            return WOMEN_MENU

        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=clothes_size_keyboard(),
    )
    return SIZE_CLOTHES


# --- Обувь ---

async def shoes_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in SHOES_SUBCATS:
        code = SHOES_SUBCATS[text]
        set_basic_context(context, gender="unisex", main_category="shoes")
        set_subcategory(context, code, text)

        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SIZE_SHOES

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=shoes_menu_keyboard(),
    )
    return SHOES_MENU


async def size_shoes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Обувь. Выберите тип:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text in SHOES_SIZES:
        set_size(context, "shoes", text)
        summary = build_selection_summary(context)
        await update.message.reply_text(summary)

        await update.message.reply_text(
            "Обувь. Выберите тип:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=shoes_size_keyboard(),
    )
    return SIZE_SHOES


# --- main() ---

def main() -> None:
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outer_menu_router)
            ],
            WOMEN_OUTER_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outer_menu_router)
            ],
            SIZE_CLOTHES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, size_clothes_router)
            ],
            SHOES_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_menu_router)
            ],
            SIZE_SHOES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, size_shoes_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
