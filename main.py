import os
import json
import logging

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ===== ЛОГИ =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ===== ТОКЕН БОТА =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# ===== (ОПЦИОНАЛЬНО) GOOGLE SHEETS =====
SHEET = None
try:
    gs_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    gs_sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if gs_json and gs_sheet_id:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_dict = json.loads(gs_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
        SHEET = client.open_by_key(gs_sheet_id).sheet1
        logger.info("Google Sheets connected successfully")
    else:
        logger.info("Google Sheets: env vars not set, skipping")
except Exception as e:
    logger.error("Google Sheets init error: %s", e)
    SHEET = None

# ===== СОСТОЯНИЯ ДЛЯ ДИАЛОГА =====
MAIN_MENU, MEN_MENU, WOMEN_MENU, SHOES_MENU = range(4)

# ===== КОНСТАНТЫ =====

CLOTHES_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

SHOES_CATEGORIES = ["Кроссовки", "Кеды", "Сланцы", "Ботинки"]

SHOES_SIZES = [
    "34", "34,5", "35", "35,5",
    "36", "36,5", "37", "37,5",
    "38", "38,5", "39", "39,5",
    "40", "40,5", "41", "41,5",
    "42", "42,5", "43", "43,5",
    "44", "44,5", "45", "45,5",
    "46",
]

# ===== КЛАВИАТУРЫ =====


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


def clothes_size_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(size) for size in CLOTHES_SIZES],
        [KeyboardButton("Назад к категориям"), KeyboardButton("Назад в меню")],
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
    row = []
    for s in SHOES_SIZES:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [KeyboardButton("Назад к категориям"), KeyboardButton("Назад в меню")]
    )
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ===== ВСПОМОГАТЕЛЬНОЕ: ЗАПРОС ТОВАРОВ (пока заглушка) =====


def make_fake_items_text(
    gender: str,
    main_category: str,
    subcategory: str,
    size_group: str,
    size_value: str,
) -> str:
    """
    Пока вместо Google Sheets возвращаем текст-заглушку.
    Позже сюда подключим чтение из таблицы.
    """
    return (
        f"Здесь будут товары:\n"
        f"- Пол: {gender}\n"
        f"- Раздел: {main_category}\n"
        f"- Подкатегория: {subcategory}\n"
        f"- Размерная группа: {size_group}\n"
        f"- Размер: {size_value}\n\n"
        f"Когда подключим таблицу, бот будет подставлять реальные вещи."
    )


# ===== ХЕНДЛЕРЫ =====


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# --- ГЛАВНОЕ МЕНЮ ---


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
        await update.message.reply_text(
            "Раздел аксессуаров пока в разработке.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Обувь":
        await update.message.reply_text(
            "Раздел обуви. Выберите категорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text == "Распродажа":
        await update.message.reply_text(
            "Раздел распродажи пока в разработке.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Моя корзина":
        await update.message.reply_text(
            "Корзина пока пустая.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# --- МУЖСКАЯ ОДЕЖДА ---


async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # навигация
    if text == "Назад в меню":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Назад к категориям":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    # выбор подкатегории
    men_subcats = [
        "Сумки | Рюкзаки",
        "Верхняя одежда",
        "Футболки",
        "Головные уборы",
        "Штаны | Шорты",
    ]

    if text in men_subcats:
        context.user_data["current"] = {
            "gender": "M",
            "main_category": "Одежда",
            "subcategory": text,
            "size_group": "Одежда",
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_MENU

    # выбор размера
    if text in CLOTHES_SIZES and "current" in context.user_data:
        current = context.user_data["current"]
        msg = make_fake_items_text(
            gender=current["gender"],
            main_category=current["main_category"],
            subcategory=current["subcategory"],
            size_group=current["size_group"],
            size_value=text,
        )
        await update.message.reply_text(msg)
        return MEN_MENU

    await update.message.reply_text(
        "Выберите подкатегорию или размер из списка."
    )
    return MEN_MENU


# --- ЖЕНСКАЯ ОДЕЖДА ---


async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Назад к категориям":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    women_subcats = [
        "Сумки",
        "Головные уборы",
        "Футболки | Топы",
        "Верхняя одежда",
        "Штаны | Шорты",
    ]

    if text in women_subcats:
        context.user_data["current"] = {
            "gender": "F",
            "main_category": "Одежда",
            "subcategory": text,
            "size_group": "Одежда",
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_MENU

    if text in CLOTHES_SIZES and "current" in context.user_data:
        current = context.user_data["current"]
        msg = make_fake_items_text(
            gender=current["gender"],
            main_category=current["main_category"],
            subcategory=current["subcategory"],
            size_group=current["size_group"],
            size_value=text,
        )
        await update.message.reply_text(msg)
        return WOMEN_MENU

    await update.message.reply_text(
        "Выберите подкатегорию или размер из списка."
    )
    return WOMEN_MENU


# --- ОБУВЬ ---


async def shoes_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Назад к категориям":
        context.user_data.pop("current", None)
        await update.message.reply_text(
            "Обувь. Выберите категорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    # выбор подкатегории обуви
    if text in SHOES_CATEGORIES:
        context.user_data["current"] = {
            "gender": "UNI",
            "main_category": "Обувь",
            "subcategory": text,
            "size_group": "Обувь",
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_MENU

    # выбор размера обуви
    if text in SHOES_SIZES and "current" in context.user_data:
        current = context.user_data["current"]
        msg = make_fake_items_text(
            gender=current["gender"],
            main_category=current["main_category"],
            subcategory=current["subcategory"],
            size_group=current["size_group"],
            size_value=text,
        )
        await update.message.reply_text(msg)
        return SHOES_MENU

    await update.message.reply_text(
        "Выберите категорию обуви или размер из списка."
    )
    return SHOES_MENU


# ===== MAIN =====


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
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
