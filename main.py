import os
import json
import logging
from typing import Dict, Any, List, Optional

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
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ----------------- ЛОГИ -----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------- ENV -----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

if not GOOGLE_SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

# ----------------- GOOGLE SHEETS -----------------


def create_gspread_client() -> gspread.Client:
    """Создаём клиента gspread из JSON сервисного аккаунта в переменной окружения."""
    creds_dict = json.loads(SERVICE_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client


def get_worksheet():
    client = create_gspread_client()
    sh = client.open_by_key(GOOGLE_SHEET_ID)
    # первая вкладка (у тебя она называется "Лист1")
    return sh.sheet1


def normalize(s: Optional[str]) -> str:
    """Нормализуем строку: lower + без пробелов. Для сравнения категорий и т.п."""
    if s is None:
        return ""
    return "".join(str(s).split()).lower()


def normalize_size(s: Optional[str]) -> str:
    """Нормализуем размер: заменяем запятую на точку, обрезаем пробелы."""
    if s is None:
        return ""
    return str(s).replace(",", ".").strip()


def load_catalog_rows() -> List[Dict[str, Any]]:
    """Читаем все строки таблицы в список словарей по шапке."""
    ws = get_worksheet()
    rows = ws.get_all_records()  # первая строка – заголовки
    return rows


def filter_products(
    rows: List[Dict[str, Any]],
    *,
    main_category: Optional[str] = None,
    subcategory: Optional[str] = None,
    size_group: Optional[str] = None,
    size: Optional[str] = None,
    gender: Optional[str] = None,
    ignore_gender: bool = False,
) -> List[Dict[str, Any]]:
    """Фильтрация товаров по набору параметров.

    - сравнение категорий/подкатегорий/size_group – без регистра и пробелов;
    - размер – с приведением запятых/точек;
    - gender:
        * если ignore_gender=True – пол не учитываем (обувь);
        * если False – подойдут строки, где Gender == выбранному полу или Unisex.
    """

    def row_match(row: Dict[str, Any]) -> bool:
        # Gender
        if not ignore_gender:
            row_gender = normalize(row.get("Gender", ""))
            if gender:
                g = normalize(gender)
                # допускаем Unisex / Унисекс / Any / пусто
                if row_gender not in {g, "unisex", "унисекс", "any", "all", ""}:
                    return False

        # Main_category
        if main_category:
            if normalize(row.get("Main_category")) != normalize(main_category):
                return False

        # Subcategory
        if subcategory:
            if normalize(row.get("Subcategory")) != normalize(subcategory):
                return False

        # Size_group
        if size_group:
            if normalize(row.get("Size_group")) != normalize(size_group):
                return False

        # Size
        if size:
            if normalize_size(row.get("Size")) != normalize_size(size):
                return False

        return True

    return [r for r in rows if row_match(r)]


# ----------------- СОСТОЯНИЯ DIALOG -----------------

(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    MEN_TOP_TYPE,
    MEN_TOP_SIZE,
    WOMEN_TOP_TYPE,
    WOMEN_TOP_SIZE,
    SHOES_TYPE,
    SHOES_SIZE,
) = range(9)

# ----------------- КЛАВИАТУРЫ -----------------


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
        [KeyboardButton("XS"), KeyboardButton("S"), KeyboardButton("M")],
        [KeyboardButton("L"), KeyboardButton("XL"), KeyboardButton("XXL")],
        [KeyboardButton("Назад к категориям")],
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
    # 34–46, включая половинки
    row1 = [KeyboardButton(str(s)) for s in range(34, 39)]
    row2 = [KeyboardButton(str(s)) for s in range(39, 44)]
    row3 = [KeyboardButton(str(s)) for s in range(44, 47)]
    # половинки
    halves = ["35.5", "36.5", "37.5", "38.5", "39.5", "40.5", "41.5", "42.5", "43.5", "44.5"]
    row4 = [KeyboardButton(h) for h in halves[:5]]
    row5 = [KeyboardButton(h) for h in halves[5:]]
    back = [KeyboardButton("Назад к категориям")]
    keyboard = [row1, row2, row3, row4, row5, back]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ----------------- КОРЗИНА -----------------


def get_cart(user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "cart" not in user_data:
        user_data["cart"] = []
    return user_data["cart"]


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = get_cart(context.user_data)
    if not cart:
        await update.message.reply_text("Корзина пока пустая.", reply_markup=main_menu_keyboard())
        return MAIN_MENU

    lines = []
    total = 0
    for item in cart:
        price_str = str(item.get("Price", "0")).strip()
        try:
            price = float(price_str.replace(",", "."))
        except ValueError:
            price = 0.0
        total += price
        lines.append(f"- {item.get('Title', '')} | размер {item.get('Size', '')} | {price_str}")

    lines.append(f"\nИтого: {total}")
    await update.message.reply_text("\n".join(lines), reply_markup=main_menu_keyboard())
    return MAIN_MENU


# ----------------- ПОКАЗ ТОВАРОВ -----------------


async def send_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product: Dict[str, Any],
):
    """Показываем один товар: описание + кнопка 'Добавить в корзину'."""
    text_parts = []

    title = product.get("Title", "")
    if title:
        text_parts.append(f"Название: {title}")

    size = product.get("Size", "")
    if size:
        text_parts.append(f"Размер: {size}")

    desc = product.get("Description", "")
    if desc:
        text_parts.append(f"Описание: {desc}")

    condition = product.get("Condition", "")
    if condition:
        text_parts.append(f"Состояние: {condition}")

    price = product.get("Price", "")
    if price:
        text_parts.append(f"Цена: {price}")

    text = "\n".join(text_parts) if text_parts else "Товар"

    product_id = str(product.get("ID", ""))

    # сохраняем товар в bot_data, чтобы по ID можно было добавить в корзину
    products_by_id = context.bot_data.setdefault("products_by_id", {})
    products_by_id[product_id] = product

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Добавить в корзину", callback_data=f"add_to_cart:{product_id}")]]
    )

    photo_url = str(product.get("Photo_url", "")).strip()
    if photo_url and photo_url.lower() != "none":
        try:
            await update.message.reply_photo(photo=photo_url, caption=text, reply_markup=keyboard)
            return
        except Exception as e:
            logger.warning("Не удалось отправить фото: %s", e)

    await update.message.reply_text(text, reply_markup=keyboard)


async def show_products_for_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    main_category: str,
    subcategory: str,
    size_group: str,
    size: str,
    gender: Optional[str],
    ignore_gender: bool,
):
    """Общий помощник: достаём строки из таблицы, фильтруем и показываем."""

    try:
        rows = load_catalog_rows()
    except Exception as e:
        logger.exception("Ошибка при чтении таблицы: %s", e)
        await update.message.reply_text("Ошибка при чтении каталога. Попробуйте позже.")
        return

    products = filter_products(
        rows,
        main_category=main_category,
        subcategory=subcategory,
        size_group=size_group,
        size=size,
        gender=gender,
        ignore_gender=ignore_gender,
    )

    if not products:
        await update.message.reply_text("Товаров с такими параметрами пока нет.")
        return

    for p in products:
        await send_product(update, context, p)


# ----------------- HANDLERS -----------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Мужская одежда":
        context.user_data["gender"] = "Male"
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:", reply_markup=men_menu_keyboard()
        )
        return MEN_MENU

    if text == "Женская одежда":
        context.user_data["gender"] = "Female"
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    if text == "Обувь":
        # для обуви гендер не учитываем
        context.user_data["gender"] = None
        await update.message.reply_text("Обувь. Выберите тип:", reply_markup=shoes_type_keyboard())
        return SHOES_TYPE

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров пока в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        return await show_cart(update, context)

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---- Мужская одежда ----


async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "Male"

    if text == "Назад в меню":
        await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())
        return MAIN_MENU

    if text == "Верхняя одежда":
        context.user_data["clothes_subcategory"] = "Верхняя одежда"
        await update.message.reply_text(
            "Мужская верхняя одежда. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_TOP_SIZE

    if text == "Футболки":
        context.user_data["clothes_subcategory"] = "Футболки"
        await update.message.reply_text(
            "Мужские футболки. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_TOP_SIZE

    if text == "Штаны | Шорты":
        context.user_data["clothes_subcategory"] = "Штаны | Шорты"
        await update.message.reply_text(
            "Мужские штаны и шорты. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_TOP_SIZE

    # Остальные подкатегории пока без каталога
    await update.message.reply_text("Эта подкатегория пока без списка товаров.")
    return MEN_MENU


async def men_top_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    # поиск товаров в таблице
    gender = "Male"
    subcat = context.user_data.get("clothes_subcategory", "")
    size = text

    await show_products_for_selection(
        update,
        context,
        main_category="Одежда",
        subcategory=subcat,
        size_group="Одежда",
        size=size,
        gender=gender,
        ignore_gender=False,
    )

    return MEN_TOP_SIZE


# ---- Женская одежда ----


async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "Female"

    if text == "Назад в меню":
        await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())
        return MAIN_MENU

    if text == "Верхняя одежда":
        context.user_data["clothes_subcategory"] = "Верхняя одежда"
        await update.message.reply_text(
            "Женская верхняя одежда. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_TOP_SIZE

    if text == "Футболки | Топы":
        context.user_data["clothes_subcategory"] = "Футболки | Топы"
        await update.message.reply_text(
            "Футболки и топы. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_TOP_SIZE

    if text == "Штаны | Шорты":
        context.user_data["clothes_subcategory"] = "Штаны | Шорты"
        await update.message.reply_text(
            "Женские штаны и шорты. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_TOP_SIZE

    await update.message.reply_text("Эта подкатегория пока без списка товаров.")
    return WOMEN_MENU


async def women_top_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    gender = "Female"
    subcat = context.user_data.get("clothes_subcategory", "")
    size = text

    await show_products_for_selection(
        update,
        context,
        main_category="Одежда",
        subcategory=subcat,
        size_group="Одежда",
        size=size,
        gender=gender,
        ignore_gender=False,
    )

    return WOMEN_TOP_SIZE


# ---- Обувь ----


async def shoes_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())
        return MAIN_MENU

    if text in {"Кроссовки", "Кеды", "Сланцы", "Ботинки"}:
        context.user_data["shoes_subcategory"] = text
        await update.message.reply_text(
            "Обувь. Выберите размер обуви:", reply_markup=shoes_size_keyboard()
        )
        return SHOES_SIZE

    await update.message.reply_text("Выберите пункт из списка.", reply_markup=shoes_type_keyboard())
    return SHOES_TYPE


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад к категориям":
        await update.message.reply_text("Обувь. Выберите тип:", reply_markup=shoes_type_keyboard())
        return SHOES_TYPE

    size = text
    subcat = context.user_data.get("shoes_subcategory", "Кеды")

    # Для обуви гендер не учитываем, чтобы Unisex показывался всем
    await show_products_for_selection(
        update,
        context,
        main_category="Обувь",
        subcategory=subcat,
        size_group="Обувь",
        size=size,
        gender=None,
        ignore_gender=True,
    )

    return SHOES_SIZE


# ---- Callback add_to_cart ----


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith("add_to_cart:"):
        product_id = data.split(":", 1)[1]
        products_by_id = context.bot_data.get("products_by_id", {})
        product = products_by_id.get(product_id)

        if not product:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("Не удалось найти товар для добавления в корзину.")
            return

        cart = get_cart(context.user_data)
        cart.append(product)
        await query.message.reply_text("Товар добавлен в корзину.")
        return


# ----------------- MAIN APP -----------------


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router),
            ],
            MEN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_menu_router),
            ],
            WOMEN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_menu_router),
            ],
            MEN_TOP_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_top_size_router),
            ],
            WOMEN_TOP_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_top_size_router),
            ],
            SHOES_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_type_router),
            ],
            SHOES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(callback_router))

    app.run_polling()


if __name__ == "__main__":
    main()
