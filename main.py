import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

ORDERS_CHANNEL_ID = os.getenv("ORDERS_CHANNEL_ID")  # ID канала для заказов
OWNER_USERNAME = (os.getenv("OWNER_USERNAME") or "").lstrip("@")  # твой логин без @

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

if not GOOGLE_SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

if not ORDERS_CHANNEL_ID:
    raise RuntimeError("ORDERS_CHANNEL_ID is not set")

try:
    ORDERS_CHANNEL_ID_INT = int(ORDERS_CHANNEL_ID)
except ValueError:
    raise RuntimeError("ORDERS_CHANNEL_ID must be integer (e.g. -1001234567890)")

# ----------------- GOOGLE SHEETS ПОДКЛЮЧЕНИЕ -----------------
creds_dict = json.loads(SERVICE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1  # первый лист


def load_products() -> List[Dict]:
    """
    Читаем все товары как список словарей.
    Ожидаются столбцы:
    ID, Gender, Main_category, Subcategory, Size_group,
    Size, Title, Description, Condition, Price, Photo_url, Quantity
    """
    rows = sheet.get_all_records()
    return rows


# ----------------- УТИЛИТЫ -----------------
def norm(s: Optional[str]) -> str:
    """
    Нормализация строк для сравнения:
    - приводим к строке
    - обрезаем пробелы
    - в нижний регистр
    - запятые -> точки
    """
    if s is None:
        return ""
    return str(s).strip().lower().replace(",", ".")


def format_price_byn(value) -> str:
    """
    Приводим цену к строке и гарантируем суффикс BYN,
    если пользователь сам не указал валюту.
    """
    s = str(value).strip()
    if not s:
        return "0 BYN"
    low = s.lower()
    if "byn" in low or "бел" in low:
        return s
    return f"{s} BYN"


def filter_products(
    *,
    main_category: Optional[str] = None,
    subcategory: Optional[str] = None,
    size_group: Optional[str] = None,
    size: Optional[str] = None,
    gender: Optional[str] = None,
) -> List[Dict]:
    """
    Фильтр товаров по параметрам.
    gender=None — пол не учитывается (например, обувь unisex).
    Также фильтруем по количеству: Quantity <= 0 — товар не показываем.
    """
    products = load_products()
    result = []

    n_main = norm(main_category)
    n_sub = norm(subcategory)
    n_group = norm(size_group)
    n_size = norm(size)
    n_gender = norm(gender)

    for row in products:
        # Количество
        qty_raw = row.get("Quantity", "")
        try:
            qty = float(str(qty_raw).replace(",", "."))
        except ValueError:
            qty = 1.0  # если не число — считаем, что есть в наличии
        if qty <= 0:
            continue

        # Основная категория
        if n_main and norm(row.get("Main_category")) != n_main:
            continue

        # Пол (учитываем Муж/Жен + Unisex/пусто)
        row_gender = norm(row.get("Gender"))
        if n_gender:
            if row_gender not in (n_gender, "unisex", ""):
                continue

        # Подкатегория
        if n_sub and norm(row.get("Subcategory")) != n_sub:
            continue

        # Группа размеров (обувь/одежда и т.п.)
        if n_group and norm(row.get("Size_group")) != n_group:
            continue

        # Конкретный размер
        if n_size and norm(row.get("Size")) != n_size:
            continue

        result.append(row)

    return result


def chunk_list(lst: List[str], n: int) -> List[List[str]]:
    """Разбивает список на подсписки длины n."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def render_cart_text(cart: List[Dict]) -> str:
    """Текстовое представление корзины с суммой."""
    if not cart:
        return "Ваша корзина пока пустая."

    lines = []
    total = 0.0

    for idx, item in enumerate(cart, 1):
        title = item.get("Title") or "Без названия"
        price_raw = item.get("Price") or "0"
        price_str = format_price_byn(price_raw)

        # Вытащить числовую часть для суммирования
        s = str(price_raw)
        num = "".join(ch for ch in s if (ch.isdigit() or ch in ",."))
        try:
            val = float(num.replace(",", ".")) if num else 0.0
        except ValueError:
            val = 0.0
        total += val

        lines.append(f"{idx}) {title} — {price_str}")

    return (
        "Ваша корзина:\n\n"
        + "\n".join(lines)
        + f"\n\nИтого: {format_price_byn(total)}"
    )


# ----------------- КЛАВИАТУРЫ -----------------
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Мужская одежда"), KeyboardButton("Женская одежда")],
        [KeyboardButton("Аксессуары"), KeyboardButton("Обувь")],
        [KeyboardButton("Распродажа"), KeyboardButton("Моя корзина")],
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
    """
    Размеры: 34, 34.5, 35, 35.5, ..., 45.5, 46
    Внизу кнопка "Назад к категориям".
    """
    sizes = []
    x = 34.0
    while x <= 46.0 + 1e-9:
        if x.is_integer():
            sizes.append(str(int(x)))
        else:
            sizes.append(f"{x:.1f}")
        x += 0.5

    rows = [list(map(KeyboardButton, row)) for row in chunk_list(sizes, 4)]
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def clothes_size_keyboard() -> ReplyKeyboardMarkup:
    """Размерная сетка одежды XS–XXL (без XXXL)."""
    sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    rows = [list(map(KeyboardButton, sizes))]
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def cart_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Удалить позицию"), KeyboardButton("Оформить заказ")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def checkout_method_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Личная встреча (Минск)")],
        [KeyboardButton("Доставка почтой")],
        [KeyboardButton("Назад в корзину")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def checkout_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton("Отмена оформления")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ----------------- СОСТОЯНИЯ ДИАЛОГА -----------------
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_TYPE,
    SHOES_SIZE,
    CART_MENU,
    CART_REMOVE,
    CHECKOUT_METHOD,
    CHECKOUT_MEET_PHONE,
    CHECKOUT_POST_DETAILS,
) = range(10)

# ----------------- КОРЗИНА -----------------
def get_cart(user_data: dict) -> List[Dict]:
    return user_data.setdefault("cart", [])


# ----------------- ХЕНДЛЕРЫ -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- ГЛАВНОЕ МЕНЮ ----------
async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Мужская одежда":
        context.user_data["gender"] = "муж"
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("Сумки | Рюкзаки"), KeyboardButton("Верхняя одежда")],
                    [KeyboardButton("Футболки"), KeyboardButton("Головные уборы")],
                    [KeyboardButton("Штаны | Шорты")],
                    [KeyboardButton("Назад в меню")],
                ],
                resize_keyboard=True,
            ),
        )
        return MEN_MENU

    if text == "Женская одежда":
        context.user_data["gender"] = "жен"
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("Сумки"), KeyboardButton("Головные уборы")],
                    [
                        KeyboardButton("Футболки | Топы"),
                        KeyboardButton("Верхняя одежда"),
                    ],
                    [KeyboardButton("Штаны | Шорты")],
                    [KeyboardButton("Назад в меню")],
                ],
                resize_keyboard=True,
            ),
        )
        return WOMEN_MENU

    if text == "Обувь":
        # Для обуви gender не фильтруем (unisex/любой пол)
        context.user_data["gender"] = None
        await update.message.reply_text(
            "Обувь. Выберите тип:", reply_markup=shoes_type_keyboard()
        )
        return SHOES_TYPE

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров пока в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        cart = get_cart(context.user_data)
        text_cart = render_cart_text(cart)
        if not cart:
            await update.message.reply_text(
                text_cart, reply_markup=main_menu_keyboard()
            )
            return MAIN_MENU

        await update.message.reply_text(
            text_cart, reply_markup=cart_menu_keyboard()
        )
        return CART_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- МУЖСКАЯ ОДЕЖДА ----------
async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "муж"

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text in (
        "Сумки | Рюкзаки",
        "Верхняя одежда",
        "Футболки",
        "Головные уборы",
        "Штаны | Шорты",
    ):
        context.user_data["current_main_category"] = "Одежда"
        context.user_data["current_subcategory"] = text
        context.user_data["gender"] = gender
        await update.message.reply_text(
            f"Мужская {text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return MEN_MENU

    if text in ("XS", "S", "M", "L", "XL", "XXL"):
        main_cat = context.user_data.get("current_main_category")
        subcat = context.user_data.get("current_subcategory")

        products = filter_products(
            main_category=main_cat,
            subcategory=subcat,
            size_group="одежда",
            size=text,
            gender=gender,
        )

        if not products:
            await update.message.reply_text(
                "Товаров с такими параметрами пока нет.",
                reply_markup=clothes_size_keyboard(),
            )
            return MEN_MENU

        await send_products(update, context, products)
        return MEN_MENU

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=clothes_size_keyboard(),
    )
    return MEN_MENU


# ---------- ЖЕНСКАЯ ОДЕЖДА ----------
async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "жен"

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text in (
        "Сумки",
        "Головные уборы",
        "Футболки | Топы",
        "Верхняя одежда",
        "Штаны | Шорты",
    ):
        context.user_data["current_main_category"] = "Одежда"
        context.user_data["current_subcategory"] = text
        context.user_data["gender"] = gender
        await update.message.reply_text(
            f"Женская {text}. Выберите размер:",
            reply_markup=clothes_size_keyboard(),
        )
        return WOMEN_MENU

    if text in ("XS", "S", "M", "L", "XL", "XXL"):
        main_cat = context.user_data.get("current_main_category")
        subcat = context.user_data.get("current_subcategory")

        products = filter_products(
            main_category=main_cat,
            subcategory=subcat,
            size_group="одежда",
            size=text,
            gender=gender,
        )

        if not products:
            await update.message.reply_text(
                "Товаров с такими параметрами пока нет.",
                reply_markup=clothes_size_keyboard(),
            )
            return WOMEN_MENU

        await send_products(update, context, products)
        return WOMEN_MENU

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=clothes_size_keyboard(),
    )
    return WOMEN_MENU


# ---------- ОБУВЬ: ТИП ----------
async def shoes_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text in ("Кроссовки", "Кеды", "Сланцы", "Ботинки"):
        context.user_data["shoes_subcategory"] = text
        await update.message.reply_text(
            "Обувь. Выберите размер обуви:", reply_markup=shoes_size_keyboard()
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите тип из списка.", reply_markup=shoes_type_keyboard()
    )
    return SHOES_TYPE


# ---------- ОБУВЬ: РАЗМЕР ----------
async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Обувь. Выберите тип:", reply_markup=shoes_type_keyboard()
        )
        return SHOES_TYPE

    # проверяем, что это размер из сетки
    allowed_sizes = set()
    x = 34.0
    while x <= 46.0 + 1e-9:
        if x.is_integer():
            allowed_sizes.add(str(int(x)))
        else:
            allowed_sizes.add(f"{x:.1f}")
        x += 0.5

    if text not in allowed_sizes:
        await update.message.reply_text(
            "Выберите размер из списка.", reply_markup=shoes_size_keyboard()
        )
        return SHOES_SIZE

    subcat = context.user_data.get("shoes_subcategory")

    products = filter_products(
        main_category="обувь",
        subcategory=subcat,
        size_group="обувь",
        size=text,
        gender=None,  # обувь может быть unisex
    )

    if not products:
        await update.message.reply_text(
            "Товаров с такими параметрами пока нет.",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await send_products(update, context, products)
    return SHOES_SIZE


# ---------- КОРЗИНА: МЕНЮ ----------
async def cart_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    cart = get_cart(context.user_data)

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if not cart:
        await update.message.reply_text(
            "Ваша корзина пока пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Удалить позицию":
        await update.message.reply_text(
            render_cart_text(cart)
            + "\n\nВведите номер позиции, которую нужно удалить.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Назад в корзину")]],
                resize_keyboard=True,
            ),
        )
        return CART_REMOVE

    if text == "Оформить заказ":
        await update.message.reply_text(
            "Выберите способ получения заказа:",
            reply_markup=checkout_method_keyboard(),
        )
        return CHECKOUT_METHOD

    # Любой другой текст — снова показываем корзину
    await update.message.reply_text(
        render_cart_text(cart), reply_markup=cart_menu_keyboard()
    )
    return CART_MENU


# ---------- КОРЗИНА: УДАЛЕНИЕ ----------
async def cart_remove_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    cart = get_cart(context.user_data)

    if text == "Назад в корзину":
        if not cart:
            await update.message.reply_text(
                "Ваша корзина пока пустая.", reply_markup=main_menu_keyboard()
            )
            return MAIN_MENU
        await update.message.reply_text(
            render_cart_text(cart), reply_markup=cart_menu_keyboard()
        )
        return CART_MENU

    if not cart:
        await update.message.reply_text(
            "Корзина уже пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    try:
        idx = int(text)
    except ValueError:
        await update.message.reply_text(
            "Некорректный номер позиции. Введите число или нажмите 'Назад в корзину'.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Назад в корзину")]],
                resize_keyboard=True,
            ),
        )
        return CART_REMOVE

    if not (1 <= idx <= len(cart)):
        await update.message.reply_text(
            "Номер вне диапазона. Попробуйте ещё раз или нажмите 'Назад в корзину'.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Назад в корзину")]],
                resize_keyboard=True,
            ),
        )
        return CART_REMOVE

    removed = cart.pop(idx - 1)
    await update.message.reply_text(
        f"Позиция '{removed.get('Title')}' удалена из корзины."
    )

    if not cart:
        await update.message.reply_text(
            "Корзина теперь пустая.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text(
        render_cart_text(cart), reply_markup=cart_menu_keyboard()
    )
    return CART_MENU


# ---------- ОФОРМЛЕНИЕ: ВЫБОР СПОСОБА ----------
async def checkout_method_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    cart = get_cart(context.user_data)

    if not cart:
        await update.message.reply_text(
            "Корзина пустая. Нечего оформлять.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == "Назад в корзину":
        await update.message.reply_text(
            render_cart_text(cart), reply_markup=cart_menu_keyboard()
        )
        return CART_MENU

    if text == "Личная встреча (Минск)":
        context.user_data["checkout_method"] = "meet"
        await update.message.reply_text(
            "Укажите номер телефона для связи (одним сообщением).",
            reply_markup=checkout_cancel_keyboard(),
        )
        return CHECKOUT_MEET_PHONE

    if text == "Доставка почтой":
        context.user_data["checkout_method"] = "post"
        await update.message.reply_text(
            "Отправьте одним сообщением: ФИО, номер телефона, город и адрес/индекс "
            "или номер отделения (если это Европочта).",
            reply_markup=checkout_cancel_keyboard(),
        )
        return CHECKOUT_POST_DETAILS

    await update.message.reply_text(
        "Выберите вариант из списка.",
        reply_markup=checkout_method_keyboard(),
    )
    return CHECKOUT_METHOD


# ---------- ОФОРМЛЕНИЕ: ЛИЧНАЯ ВСТРЕЧА ----------
async def checkout_meet_phone_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    if text == "Отмена оформления":
        cart = get_cart(context.user_data)
        if not cart:
            await update.message.reply_text(
                "Корзина пустая.", reply_markup=main_menu_keyboard()
            )
            return MAIN_MENU
        await update.message.reply_text(
            render_cart_text(cart), reply_markup=cart_menu_keyboard()
        )
        return CART_MENU

    phone = text
    method = "Личная встреча (Минск)"
    extra_details = f"Телефон: {phone}"

    return await finalize_order(update, context, method, extra_details)


# ---------- ОФОРМЛЕНИЕ: ДОСТАВКА ПОЧТОЙ ----------
async def checkout_post_details_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    if text == "Отмена оформления":
        cart = get_cart(context.user_data)
        if not cart:
            await update.message.reply_text(
                "Корзина пустая.", reply_markup=main_menu_keyboard()
            )
            return MAIN_MENU
        await update.message.reply_text(
            render_cart_text(cart), reply_markup=cart_menu_keyboard()
        )
        return CART_MENU

    method = "Доставка почтой"
    extra_details = text  # тут всё сразу: ФИО, телефон, город, адрес/индекс/отделение

    return await finalize_order(update, context, method, extra_details)


# ---------- ФИНАЛИЗАЦИЯ ЗАКАЗА ----------
async def finalize_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    method: str,
    extra_details: str,
) -> int:
    cart = get_cart(context.user_data)
    if not cart:
        await update.message.reply_text(
            "Корзина пустая. Нечего оформлять.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    # Собираем заказ
    order_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    user = update.effective_user
    username = f"@{user.username}" if user.username else "(username отсутствует)"

    lines = []
    total = 0.0
    for idx, item in enumerate(cart, 1):
        title = item.get("Title") or "Без названия"
        price_raw = item.get("Price") or "0"
        price_str = format_price_byn(price_raw)

        s = str(price_raw)
        num = "".join(ch for ch in s if (ch.isdigit() or ch in ",."))
        try:
            val = float(num.replace(",", ".")) if num else 0.0
        except ValueError:
            val = 0.0
        total += val

        lines.append(f"{idx}) {title} — {price_str}")

    items_block = "Состав заказа:\n" + "\n".join(lines)
    total_line = f"Итого: {format_price_byn(total)}"

    buyer_block = (
        f"Покупатель: {user.full_name}\n"
        f"Username: {username}\n"
        f"User ID: {user.id}"
    )

    delivery_block = f"Способ получения: {method}\nДетали:\n{extra_details}"

    contact_line = ""
    if OWNER_USERNAME:
        contact_line = f"\n\nДля связи с продавцом: @{OWNER_USERNAME}"

    text_for_channel = (
        f"Новый заказ #{order_id}\n\n"
        f"{buyer_block}\n\n"
        f"{delivery_block}\n\n"
        f"{items_block}\n{total_line}"
        f"{contact_line}"
    )

    text_for_user = (
        "Ваш заказ принят.\n\n"
        f"{delivery_block}\n\n"
        f"{items_block}\n{total_line}"
        f"{contact_line}"
    )

    # Отправка в канал
    try:
        await context.bot.send_message(
            chat_id=ORDERS_CHANNEL_ID_INT,
            text=text_for_channel,
        )
    except Exception as e:
        logger.error(f"Не удалось отправить заказ в канал: {e}")

    # Сообщение пользователю
    await update.message.reply_text(
        text_for_user,
        reply_markup=main_menu_keyboard(),
    )

    # Очищаем корзину
    cart.clear()

    return MAIN_MENU


# ---------- ОТПРАВКА ТОВАРОВ ----------
async def send_products(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    products: List[Dict],
):
    """
    Показывает товары: состояние + размер + цена BYN + фото + кнопка "Добавить в корзину".
    """
    chat_id = update.effective_chat.id

    for row in products:
        title = row.get("Title") or "Без названия"
        desc = row.get("Description") or ""
        cond = row.get("Condition") or ""
        size = row.get("Size") or ""
        price_raw = row.get("Price") or ""
        price_str = format_price_byn(price_raw)
        photo_url = row.get("Photo_url") or None
        row_id = row.get("ID")
        qty_raw = row.get("Quantity", "")

        qty_str = ""
        try:
            qty_val = float(str(qty_raw).replace(",", "."))
            if qty_val > 0:
                # если целое — без .0
                if abs(qty_val - int(qty_val)) < 1e-9:
                    qty_str = f"{int(qty_val)} шт."
                else:
                    qty_str = f"{qty_val} шт."
        except ValueError:
            pass

        text = f"{title}\n\nСостояние: {cond}\nРазмер: {size}\nЦена: {price_str}"
        if qty_str:
            text += f"\nВ наличии: {qty_str}"
        if desc:
            text += f"\n\nОписание: {desc}"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Добавить в корзину", callback_data=f"add_to_cart:{row_id}"
                    )
                ]
            ]
        )

        if photo_url and str(photo_url).lower() != "none":
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=str(photo_url),
                caption=text,
                reply_markup=keyboard,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
            )


# ---------- CALLBACK ДЛЯ КОРЗИНЫ ----------
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("add_to_cart:"):
        row_id = norm(data.split(":", 1)[1])
        products = load_products()
        for row in products:
            if norm(row.get("ID")) == row_id:
                cart = get_cart(context.user_data)
                cart.append(row)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text("Товар добавлен в корзину.")
                break
        else:
            await query.message.reply_text("Не удалось найти товар в каталоге.")


# ----------------- MAIN -----------------
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
            SHOES_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_type_router)
            ],
            SHOES_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shoes_size_router)
            ],
            CART_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cart_menu_router)
            ],
            CART_REMOVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cart_remove_router)
            ],
            CHECKOUT_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_method_router)
            ],
            CHECKOUT_MEET_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, checkout_meet_phone_router
                )
            ],
            CHECKOUT_POST_DETAILS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, checkout_post_details_router
                )
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
