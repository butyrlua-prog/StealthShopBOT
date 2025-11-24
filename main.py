import os
import json
import logging
from typing import Any, Dict, List, Optional

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

# ------------------ ЛОГИРОВАНИЕ ------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ------------------ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

if not SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

# ------------------ ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ------------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds_dict = json.loads(SERVICE_JSON)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

# Будем держать продукты в кэше по ID (для корзины и т.п.)
PRODUCTS_BY_ID: Dict[str, Dict[str, Any]] = {}


def reload_catalog() -> List[Dict[str, Any]]:
    """Читает всю таблицу, обновляет кэш по ID и возвращает список товаров."""
    records = sheet.get_all_records()
    PRODUCTS_BY_ID.clear()
    for row in records:
        prod_id = str(row.get("ID") or "").strip()
        if prod_id:
            PRODUCTS_BY_ID[prod_id] = row
    return records


# ------------------ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ НОРМАЛИЗАЦИИ ------------------

def norm_key(value: Any) -> str:
    """Нормализация для категорий/подкатегорий и т.п."""
    return str(value).strip().lower()


def norm_size(value: Any) -> str:
    """Нормализация для размеров (замена запятой на точку)."""
    return str(value).strip().lower().replace(",", ".")


def filter_products(
    main_category: Optional[str] = None,
    subcategory: Optional[str] = None,
    size_group: Optional[str] = None,
    size: Optional[str] = None,
    gender: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Фильтрация товаров с учётом:
    - регистр/пробелы игнорируются
    - для размеров запятая/точка не важны
    - gender, если None, не фильтруется
    """
    records = reload_catalog()
    result: List[Dict[str, Any]] = []

    main_category_n = norm_key(main_category) if main_category else None
    subcategory_n = norm_key(subcategory) if subcategory else None
    size_group_n = norm_key(size_group) if size_group else None
    size_n = norm_size(size) if size else None
    gender_n = norm_key(gender) if gender else None

    for row in records:
        if main_category_n and norm_key(row.get("Main_category")) != main_category_n:
            continue

        if subcategory_n and norm_key(row.get("Subcategory")) != subcategory_n:
            continue

        if size_group_n and norm_key(row.get("Size_group")) != size_group_n:
            continue

        if size_n and norm_size(row.get("Size")) != size_n:
            continue

        # Пол фильтруем только если явно задан
        if gender_n is not None:
            if norm_key(row.get("Gender")) != gender_n:
                continue

        result.append(row)

    return result


# ------------------ КЛАВИАТУРЫ ------------------

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
        [KeyboardButton("Футболки (муж)"), KeyboardButton("Головные уборы (муж)")],
        [KeyboardButton("Штаны | Шорты (муж)")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Сумки (жен)"), KeyboardButton("Головные уборы (жен)")],
        [KeyboardButton("Футболки | Топы (жен)"), KeyboardButton("Верхняя одежда (жен)")],
        [KeyboardButton("Штаны | Шорты (жен)")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clothes_size_keyboard() -> ReplyKeyboardMarkup:
    # Без XXXL, только до XXL
    keyboard = [
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL"), KeyboardButton("XXL")],
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
    # Размеры 34–46, включая половинки .5 именно с ТОЧКОЙ
    sizes = [
        "34", "34.5", "35", "35.5",
        "36", "36.5", "37", "37.5",
        "38", "38.5", "39", "39.5",
        "40", "40.5", "41", "41.5",
        "42", "42.5", "43", "43.5",
        "44", "44.5", "45", "45.5",
        "46",
    ]

    # Делаем по 4 в ряд
    rows: List[List[KeyboardButton]] = []
    row: List[KeyboardButton] = []
    for s in sizes:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ------------------ СОСТОЯНИЯ ДИАЛОГА ------------------

(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    CLOTHES_SIZE,
    SHOES_CATEGORY,
    SHOES_SIZE,
) = range(6)

# ------------------ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ БОТА ------------------

async def send_products(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    main_category: str,
    subcategory: str,
    size_group: str,
    size: str,
    gender: Optional[str] = None,
) -> None:
    """Ищет товары в таблице и отправляет пользователю."""
    products = filter_products(
        main_category=main_category,
        subcategory=subcategory,
        size_group=size_group,
        size=size,
        gender=gender,
    )

    if not products:
        await update.message.reply_text("Для этого размера пока нет товаров.")
        return

    for row in products:
        title = row.get("Title") or "Без названия"
        description = row.get("Description") or ""
        condition = row.get("Condition") or ""
        price = row.get("Price") or ""
        photo_url = str(row.get("Photo_url") or "").strip()
        size_val = row.get("Size") or size

        text_parts = [title]
        if description:
            text_parts.append(description)
        if condition:
            text_parts.append(f"Состояние: {condition}")
        text_parts.append(f"Размер: {size_val}")
        if price:
            text_parts.append(f"Цена: {price}")

        text = "\n".join(text_parts)

        prod_id = str(row.get("ID") or "").strip()
        markup = None
        if prod_id:
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Добавить в корзину", callback_data=f"add:{prod_id}"
                        )
                    ]
                ]
            )

        if photo_url and photo_url.lower() != "none":
            try:
                await update.message.reply_photo(
                    photo=photo_url,
                    caption=text,
                    reply_markup=markup,
                )
            except Exception as e:
                logger.warning("Ошибка при отправке фото: %s", e)
                await update.message.reply_text(text, reply_markup=markup)
        else:
            await update.message.reply_text(text, reply_markup=markup)


def add_to_cart(context: ContextTypes.DEFAULT_TYPE, product_id: str) -> None:
    cart: List[str] = context.user_data.setdefault("cart", [])
    cart.append(product_id)


def get_cart_items(context: ContextTypes.DEFAULT_TYPE) -> List[Dict[str, Any]]:
    cart_ids: List[str] = context.user_data.get("cart", [])
    items: List[Dict[str, Any]] = []
    for pid in cart_ids:
        product = PRODUCTS_BY_ID.get(pid)
        if product:
            items.append(product)
    return items


# ------------------ ХЕНДЛЕРЫ ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

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

    if text == "Обувь":
        await update.message.reply_text(
            "Обувь. Выберите тип:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров пока в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        items = get_cart_items(context)
        if not items:
            await update.message.reply_text("Ваша корзина пока пуста.")
            return MAIN_MENU

        total_lines = []
        for row in items:
            title = row.get("Title") or "Без названия"
            price = row.get("Price") or ""
            size_val = row.get("Size") or ""
            line = title
            if size_val:
                line += f" (размер {size_val})"
            if price:
                line += f" - {price}"
            total_lines.append(line)

        text_cart = "Ваша корзина:\n\n" + "\n".join(total_lines)
        await update.message.reply_text(text_cart)
        return MAIN_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# -------- Мужская одежда --------

async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    # Для одежды пол фиксируем как "m"
    context.user_data["gender"] = "m"
    context.user_data["main_category"] = "Мужская одежда"

    if text == "Футболки (муж)":
        context.user_data["subcategory"] = "Футболки"
        context.user_data["size_group"] = "Одежда"
    elif text == "Штаны | Шорты (муж)":
        context.user_data["subcategory"] = "Штаны | Шорты"
        context.user_data["size_group"] = "Одежда"
    elif text == "Верхняя одежда (муж)":
        context.user_data["subcategory"] = "Верхняя одежда"
        context.user_data["size_group"] = "Верхняя одежда"
    elif text == "Головные уборы (муж)":
        context.user_data["subcategory"] = "Головные уборы"
        context.user_data["size_group"] = "Головные уборы"
    elif text == "Сумки | Рюкзаки":
        context.user_data["subcategory"] = "Сумки | Рюкзаки"
        context.user_data["size_group"] = "Аксессуары"
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")
        return MEN_MENU

    await update.message.reply_text(
        "Выберите размер:", reply_markup=clothes_size_keyboard()
    )
    return CLOTHES_SIZE


# -------- Женская одежда --------

async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    # Пол "f"
    context.user_data["gender"] = "f"
    context.user_data["main_category"] = "Женская одежда"

    if text == "Футболки | Топы (жен)":
        context.user_data["subcategory"] = "Футболки | Топы"
        context.user_data["size_group"] = "Одежда"
    elif text == "Штаны | Шорты (жен)":
        context.user_data["subcategory"] = "Штаны | Шорты"
        context.user_data["size_group"] = "Одежда"
    elif text == "Верхняя одежда (жен)":
        context.user_data["subcategory"] = "Верхняя одежда"
        context.user_data["size_group"] = "Верхняя одежда"
    elif text == "Головные уборы (жен)":
        context.user_data["subcategory"] = "Головные уборы"
        context.user_data["size_group"] = "Головные уборы"
    elif text == "Сумки (жен)":
        context.user_data["subcategory"] = "Сумки"
        context.user_data["size_group"] = "Аксессуары"
    else:
        await update.message.reply_text("Выберите подкатегорию из списка.")
        return WOMEN_MENU

    await update.message.reply_text(
        "Выберите размер:", reply_markup=clothes_size_keyboard()
    )
    return CLOTHES_SIZE


# -------- Выбор размера одежды --------

async def clothes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if text == "НАЗАД К КАТЕГОРИЯМ":
        gender = context.user_data.get("gender")
        if gender == "m":
            await update.message.reply_text(
                "Мужская одежда. Выберите подкатегорию:",
                reply_markup=men_menu_keyboard(),
            )
            return MEN_MENU
        else:
            await update.message.reply_text(
                "Женская одежда. Выберите подкатегорию:",
                reply_markup=women_menu_keyboard(),
            )
            return WOMEN_MENU

    size = text  # XS/S/M/... уже нормально

    await send_products(
        update,
        context,
        main_category=context.user_data.get("main_category", ""),
        subcategory=context.user_data.get("subcategory", ""),
        size_group=context.user_data.get("size_group", "Одежда"),
        size=size,
        gender=context.user_data.get("gender"),
    )

    # Остаёмся в состоянии выбора размера
    return CLOTHES_SIZE


# -------- Обувь --------

async def shoes_category_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text not in {"Кроссовки", "Кеды", "Сланцы", "Ботинки"}:
        await update.message.reply_text("Выберите тип обуви из списка.")
        return SHOES_CATEGORY

    context.user_data["main_category"] = "Обувь"
    context.user_data["subcategory"] = text
    context.user_data["size_group"] = "Обувь"
    # Для обуви гендер не фильтруем вообще (Unisex)
    context.user_data["gender"] = None

    await update.message.reply_text(
        "Выберите размер обуви:", reply_markup=shoes_size_keyboard()
    )
    return SHOES_SIZE


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()

    if raw_text == "Назад к категориям":
        await update.message.reply_text(
            "Обувь. Выберите тип:", reply_markup=shoes_category_keyboard()
        )
        return SHOES_CATEGORY

    # Нормализуем размер: заменяем запятую на точку, режем пробелы
    size = norm_size(raw_text)

    await send_products(
        update,
        context,
        main_category="Обувь",
        subcategory=context.user_data.get("subcategory", ""),
        size_group="Обувь",
        size=size,
        gender=None,  # обувь без фильтра по полу
    )

    return SHOES_SIZE


# -------- CALLBACK (корзина) --------

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith("add:"):
        prod_id = data.split(":", 1)[1]
        add_to_cart(context, prod_id)
        await query.answer("Товар добавлен в корзину", show_alert=False)


# ------------------ MAIN ------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
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
            CLOTHES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, clothes_size_router)
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
    app.add_handler(CallbackQueryHandler(callback_router))

    app.run_polling()


if __name__ == "__main__":
    main()
