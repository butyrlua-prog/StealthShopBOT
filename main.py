import os
import logging
from typing import List

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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния диалога
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_MENU,
    SHOES_SIZE,
    MEN_OUTER_TYPE,
    WOMEN_OUTER_TYPE,
    CLOTHES_SIZE,
) = range(8)

# -----------------------
# Клавиатуры
# -----------------------

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


def men_outer_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Куртки | Плащи | Ветровки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Бомберы | Свитеры")],
        [KeyboardButton("Назад к мужской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_outer_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Куртки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Свитеры | Бомберы")],
        [KeyboardButton("Назад к женской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


CLOTHING_SIZES: List[str] = ["XS", "S", "M", "L", "XL", "XXL"]


def clothing_sizes_keyboard(back_label: str) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL"), KeyboardButton("XXL")],
        [KeyboardButton(back_label)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


SHOE_SIZES: List[str] = [
    "34", "35", "35,5", "36", "36,5",
    "37", "37,5", "38", "38,5",
    "39", "39,5", "40", "40,5",
    "41", "41,5", "42", "42,5",
    "43", "43,5", "44", "44,5",
    "45", "45,5", "46",
]


def shoes_sizes_keyboard() -> ReplyKeyboardMarkup:
    rows: List[List[KeyboardButton]] = []
    row: List[KeyboardButton] = []

    for size in SHOE_SIZES:
        row.append(KeyboardButton(size))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# -----------------------
# Хендлеры
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин. Выберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    # очищаем контекст
    context.user_data.clear()
    return MAIN_MENU


# --- Главное меню ---

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
            "Обувь. Выберите подкатегорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        await update.message.reply_text("Ваша корзина пока пуста.")
        return MAIN_MENU

    await update.message.reply_text(
        "Выберите пункт из меню.",
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
        await update.message.reply_text("Мужские сумки и рюкзаки: раздел в разработке.")
        return MEN_MENU

    if text == "Головные уборы":
        await update.message.reply_text("Мужские головные уборы: раздел в разработке.")
        return MEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите тип:",
            reply_markup=men_outer_type_keyboard(),
        )
        return MEN_OUTER_TYPE

    if text == "Футболки":
        context.user_data["gender"] = "men"
        context.user_data["clothes_category"] = "Мужские футболки"
        await update.message.reply_text(
            "Мужские футболки. Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    if text == "Штаны | Шорты":
        context.user_data["gender"] = "men"
        context.user_data["clothes_category"] = "Мужские штаны и шорты"
        await update.message.reply_text(
            "Мужские штаны и шорты. Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    await update.message.reply_text(
        "Выберите подкатегорию из списка.",
        reply_markup=men_menu_keyboard(),
    )
    return MEN_MENU


async def men_outer_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        context.user_data["gender"] = "men"
        context.user_data["clothes_category"] = f"Мужская верхняя одежда: {text}"
        await update.message.reply_text(
            "Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=men_outer_type_keyboard(),
    )
    return MEN_OUTER_TYPE


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
        await update.message.reply_text("Женские сумки: раздел в разработке.")
        return WOMEN_MENU

    if text == "Головные уборы":
        await update.message.reply_text("Женские головные уборы: раздел в разработке.")
        return WOMEN_MENU

    if text == "Верхняя одежда":
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите тип:",
            reply_markup=women_outer_type_keyboard(),
        )
        return WOMEN_OUTER_TYPE

    if text == "Футболки | Топы":
        context.user_data["gender"] = "women"
        context.user_data["clothes_category"] = "Женские футболки и топы"
        await update.message.reply_text(
            "Женские футболки и топы. Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    if text == "Штаны | Шорты":
        context.user_data["gender"] = "women"
        context.user_data["clothes_category"] = "Женские штаны и шорты"
        await update.message.reply_text(
            "Женские штаны и шорты. Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    await update.message.reply_text(
        "Выберите подкатегорию из списка.",
        reply_markup=women_menu_keyboard(),
    )
    return WOMEN_MENU


async def women_outer_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        context.user_data["gender"] = "women"
        context.user_data["clothes_category"] = f"Женская верхняя одежда: {text}"
        await update.message.reply_text(
            "Выберите размер:",
            reply_markup=clothing_sizes_keyboard("Назад к категориям"),
        )
        return CLOTHES_SIZE

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=women_outer_type_keyboard(),
    )
    return WOMEN_OUTER_TYPE


# --- Общий хендлер размеров одежды ---

async def clothes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        gender = context.user_data.get("gender")
        if gender == "men":
            await update.message.reply_text(
                "Мужская одежда. Выберите подкатегорию:",
                reply_markup=men_menu_keyboard(),
            )
            return MEN_MENU
        if gender == "women":
            await update.message.reply_text(
                "Женская одежда. Выберите подкатегорию:",
                reply_markup=women_menu_keyboard(),
            )
            return WOMEN_MENU

        # на всякий случай
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in CLOTHING_SIZES:
        gender = context.user_data.get("gender", "")
        category = context.user_data.get("clothes_category", "выбранная категория")
        await update.message.reply_text(
            f"Пока это заглушка. Здесь будут товары: {category}, размер {text}."
        )
        # остаёмся на выборе размеров
        return CLOTHES_SIZE

    await update.message.reply_text(
        "Выберите размер из списка.",
        reply_markup=clothing_sizes_keyboard("Назад к категориям"),
    )
    return CLOTHES_SIZE


# --- Обувь ---

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
            reply_markup=shoes_sizes_keyboard(),
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите подкатегорию из списка.",
        reply_markup=shoes_menu_keyboard(),
    )
    return SHOES_MENU


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Обувь. Выберите подкатегорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text in SHOE_SIZES:
        cat = context.user_data.get("shoes_category", "Обувь")
        await update.message.reply_text(
            f"Пока это заглушка. Здесь будет список: {cat}, размер {text}."
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите размер из списка.",
        reply_markup=shoes_sizes_keyboard(),
    )
    return SHOES_SIZE


# -----------------------
# Запуск бота
# -----------------------

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
            MEN_OUTER_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outer_type_router)
            ],
            WOMEN_OUTER_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outer_type_router)
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
