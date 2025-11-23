import os
import json
import logging
from typing import Dict, Any, List

import gspread
from google.oauth2.service_account import Credentials

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
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========= НАСТРОЙКИ ОКРУЖЕНИЯ =========

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
if not GOOGLE_SHEETS_ID:
    raise RuntimeError("GOOGLE_SHEETS_ID is not set")

# ========= ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS =========

_SHEET = None


def get_sheet():
    global _SHEET
    if _SHEET is not None:
        return _SHEET

    info = json.loads(SERVICE_ACCOUNT_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEETS_ID)
    _SHEET = sh.sheet1  # первый лист в таблице
    return _SHEET


# Порядок колонок в Google Sheets (строка заголовков – первая строка):
# A: Категория (например: "Мужская одежда", "Женская одежда", "Обувь")
# B: Подкатегория (например: "Футболки", "Штаны | Шорты", "Кроссовки")
# C: Пол (например: "M", "F" или пусто для обуви)
# D: Размер (например: "M", "L", "42", "39.5")
# E: Название товара
# F: Описание
# G: Цена
# H: Состояние
# I: Фото (URL или file_id Telegram)

COL_CATEGORY = 0
COL_SUBCATEGORY = 1
COL_GENDER = 2
COL_SIZE = 3
COL_TITLE = 4
COL_DESCRIPTION = 5
COL_PRICE = 6
COL_CONDITION = 7
COL_PHOTO = 8

# ========= СОСТОЯНИЯ ДИАЛОГА =========

MAIN_MENU, MEN_MENU, WOMEN_MENU, CLOTH_SIZE, SHOES_TYPE, SHOES_SIZE = range(6)

# ========= КЛАВИАТУРЫ =========


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


def cloth_size_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL"), KeyboardButton("XXL")],
        [KeyboardButton("Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    # 34–46 с половинками
    sizes: List[str] = []
    s = 34.0
    while s <= 46.0 + 1e-9:
        if s.is_integer():
            sizes.append(str(int(s)))
        else:
            sizes.append(f"{s:.1f}")
        s += 0.5

    rows: List[List[KeyboardButton]] = []
    row: List[KeyboardButton] = []
    for size in sizes:
        row.append(KeyboardButton(size))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton("Назад")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ========= КАТАЛОГ / КОРЗИНА =========


def filter_products(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Фильтрация товаров из Google Sheets по:
      category, subcategory, gender, size
    """
    sheet = get_sheet()
    data = sheet.get_all_values()
    if not data or len(data) < 2:
        return []

    _, rows = data[0], data[1:]

    results: List[Dict[str, Any]] = []
    for i, row in enumerate(rows, start=2):  # номер строки в таблице
        if len(row) <= COL_PHOTO:
            continue

        category = row[COL_CATEGORY].strip()
        subcategory = row[COL_SUBCATEGORY].strip()
        gender = row[COL_GENDER].strip()
        size = row[COL_SIZE].strip()
        title = row[COL_TITLE].strip()
        description = row[COL_DESCRIPTION].strip()
        price = row[COL_PRICE].strip()
        condition = row[COL_CONDITION].strip()
        photo = row[COL_PHOTO].strip()

        if filters.get("category") and filters["category"] != category:
            continue
        if filters.get("subcategory") and filters["subcategory"] != subcategory:
            continue
        if filters.get("gender") and filters["gender"] != gender:
            continue
        if filters.get("size") and filters["size"] != size:
            continue

        product = {
            "row": i,
            "category": category,
            "subcategory": subcategory,
            "gender": gender,
            "size": size,
            "title": title,
            "description": description,
            "price": price,
            "condition": condition,
            "photo": photo,
        }
        results.append(product)

    return results


async def show_products(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    filters: Dict[str, Any],
):
    try:
        products = filter_products(filters)
    except Exception:
        logger.exception("Error reading Google Sheets")
        await update.message.reply_text("Ошибка при чтении каталога.")
        return

    if not products:
        await update.message.reply_text("Товары по этому фильтру не найдены.")
        return

    cart = context.user_data.setdefault("cart", [])
    catalog: Dict[str, Dict[str, Any]] = context.user_data.setdefault("catalog", {})

    for p in products:
        pid = f"{p['row']}"
        catalog[pid] = p

        text_lines = [p["title"] or "Без названия"]
        if p["description"]:
            text_lines.append(p["description"])
        if p["size"]:
            text_lines.append(f"Размер: {p['size']}")
        if p["condition"]:
            text_lines.append(f"Состояние: {p['condition']}")
        if p["price"]:
            text_lines.append(f"Цена: {p['price']}")

        text = "\n".join(text_lines)

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Добавить в корзину",
                        callback_data=f"add_to_cart:{pid}",
                    )
                ]
            ]
        )

        if p["photo"]:
            try:
                await update.message.reply_photo(
                    photo=p["photo"],
                    caption=text,
                    reply_markup=kb,
                )
            except Exception:
                await update.message.reply_text(text, reply_markup=kb)
        else:
            await update.message.reply_text(text, reply_markup=kb)


# ========= ХЕНДЛЕРЫ =========


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart", [])
    context.user_data.setdefault("catalog", {})
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
            "Выберите тип обуви:",
            reply_markup=shoes_type_keyboard(),
        )
        return SHOES_TYPE

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        cart: List[str] = context.user_data.get("cart", [])
        catalog: Dict[str, Dict[str, Any]] = context.user_data.get("catalog", {})
        if not cart:
            await update.message.reply_text("Корзина пока пустая.")
        else:
            lines = []
            for pid in cart:
                p = catalog.get(pid)
                if not p:
                    continue
                lines.append(f"- {p['title']} ({p['size']}) — {p['price']}")
            if lines:
                await update.message.reply_text("Ваша корзина:\n" + "\n".join(lines))
            else:
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
        await show_products(
            update,
            context,
            {
                "category": "Мужская одежда",
                "subcategory": "Сумки | Рюкзаки",
            },
        )
        return MEN_MENU

    if text == "Головные уборы":
        await show_products(
            update,
            context,
            {
                "category": "Мужская одежда",
                "subcategory": "Головные уборы",
            },
        )
        return MEN_MENU

    if text in ("Верхняя одежда", "Футболки", "Штаны | Шорты"):
        context.user_data["current_filter"] = {
            "category": "Мужская одежда",
            "gender": "M",
            "subcategory": text,
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=cloth_size_keyboard(),
        )
        return CLOTH_SIZE

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
        await show_products(
            update,
            context,
            {
                "category": "Женская одежда",
                "subcategory": "Сумки",
            },
        )
        return WOMEN_MENU

    if text == "Головные уборы":
        await show_products(
            update,
            context,
            {
                "category": "Женская одежда",
                "subcategory": "Головные уборы",
            },
        )
        return WOMEN_MENU

    if text in ("Футболки | Топы", "Верхняя одежда", "Штаны | Шорты"):
        context.user_data["current_filter"] = {
            "category": "Женская одежда",
            "gender": "F",
            "subcategory": text,
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=cloth_size_keyboard(),
        )
        return CLOTH_SIZE

    await update.message.reply_text("Выберите подкатегорию из списка.")
    return WOMEN_MENU


async def cloth_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад":
        flt = context.user_data.get("current_filter") or {}
        if flt.get("category") == "Мужская одежда":
            await update.message.reply_text(
                "Мужская одежда. Выберите подкатегорию:",
                reply_markup=men_menu_keyboard(),
            )
            return MEN_MENU
        if flt.get("category") == "Женская одежда":
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

    if text not in ("XS", "S", "M", "L", "XL", "XXL"):
        await update.message.reply_text(
            "Выберите размер из списка.",
            reply_markup=cloth_size_keyboard(),
        )
        return CLOTH_SIZE

    flt = context.user_data.get("current_filter") or {}
    flt["size"] = text
    await show_products(update, context, flt)
    return CLOTH_SIZE


async def shoes_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in ("Кроссовки", "Кеды", "Сланцы", "Ботинки"):
        context.user_data["current_filter"] = {
            "category": "Обувь",
            "subcategory": text,
        }
        await update.message.reply_text(
            f"{text}. Выберите размер:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите тип обуви из списка.",
        reply_markup=shoes_type_keyboard(),
    )
    return SHOES_TYPE


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад":
        await update.message.reply_text(
            "Выберите тип обуви:",
            reply_markup=shoes_type_keyboard(),
        )
        return SHOES_TYPE

    flt = context.user_data.get("current_filter") or {}
    flt["size"] = text
    await show_products(update, context, flt)
    return SHOES_SIZE


async def on_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("add_to_cart:"):
        return

    pid = data.split(":", 1)[1]
    catalog: Dict[str, Dict[str, Any]] = context.user_data.get("catalog", {})
    product = catalog.get(pid)
    if not product:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Товар не найден в каталоге.")
        return

    cart: List[str] = context.user_data.setdefault("cart", [])
    cart.append(pid)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("Товар добавлен в корзину.")


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
            CLOTH_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cloth_size_router)
            ],
            SHOES_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_type_router)
            ],
            SHOES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(on_callback_query))

    app.run_polling()


if __name__ == "__main__":
    main()
