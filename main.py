import os
import json
import logging
from typing import List, Dict, Optional

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
    ApplicationHandlerStop,
)

# ----------------- КОНСТАНТЫ ССЫЛОК -----------------
REVIEWS_URL = "https://t.me/StealthShopFeedBack"
CATALOG_URL = "https://t.me/+JkbPWPOUkzU3ZDJi"
INSTAGRAM_URL = "https://www.instagram.com/_stealthshop_?igsh=Z3o1ZGxnNXdyMTB5"

# ----------------- ЛОГИ -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
ORDERS_CHANNEL_ID = os.getenv("ORDERS_CHANNEL_ID")  # канал для заказов
PHOTO_CHANNEL_ID = os.getenv("PHOTO_CHANNEL_ID")    # канал для фото (fail_id)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

if not GOOGLE_SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

if ORDERS_CHANNEL_ID:
    try:
        ORDERS_CHANNEL_ID = int(ORDERS_CHANNEL_ID)
    except ValueError:
        logger.error("ORDERS_CHANNEL_ID must be integer chat id")

if PHOTO_CHANNEL_ID:
    try:
        PHOTO_CHANNEL_ID = int(PHOTO_CHANNEL_ID)
    except ValueError:
        logger.error("PHOTO_CHANNEL_ID must be integer chat id")

# ----------------- GOOGLE SHEETS ПОДКЛЮЧЕНИЕ -----------------
creds_dict = json.loads(SERVICE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1  # Лист "Лист1" по умолчанию


def load_products() -> List[Dict]:
    """
    Читаем все товары из таблицы как список словарей.
    Ожидаются столбцы:
    ID, Gender, Main_category, Subcategory, Size_group,
    Size, Title, Description, Condition, Price, Photo_url, (опционально Quantity)
    """
    rows = sheet.get_all_records()
    return rows


# ----------------- УТИЛИТЫ -----------------
def norm(s: Optional[str]) -> str:
    """Нормализация строки: trim, lower, , -> ."""
    if s is None:
        return ""
    return str(s).strip().lower().replace(",", ".")


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
    gender=None — пол не учитывается.
    Пустые параметры не учитываются.
    """
    products = load_products()
    result: List[Dict] = []

    n_main = norm(main_category)
    n_sub = norm(subcategory)
    n_group = norm(size_group)
    n_size = norm(size)
    n_gender = norm(gender)

    for row in products:
        if n_main and norm(row.get("Main_category")) != n_main:
            continue

        row_gender = norm(row.get("Gender"))
        if n_gender:
            if row_gender not in (n_gender, "unisex", ""):
                continue

        if n_sub and norm(row.get("Subcategory")) != n_sub:
            continue

        if n_group and norm(row.get("Size_group")) != n_group:
            continue

        if n_size and norm(row.get("Size")) != n_size:
            continue

        result.append(row)

    return result


def chunk_list(lst: List[str], n: int) -> List[List[str]]:
    """Разбивает список на подсписки длины n."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def format_price_byn(price_raw) -> str:
    """Возвращает цену в BYN как строку."""
    if price_raw is None:
        return "не указана"
    s = str(price_raw).strip()
    if not s:
        return "не указана"
    if "byn" in s.lower():
        return s
    return f"{s} BYN"


def parse_price_to_float(price_raw) -> float:
    """Пытается извлечь число из цены для подсчёта итоговой суммы."""
    if price_raw is None:
        return 0.0
    s = str(price_raw)
    s = s.replace("BYN", "").replace("byn", "").strip()
    s = s.split()[0] if s else ""
    try:
        return float(s.replace(",", "."))
    except Exception:
        return 0.0


# ----------------- КЛАВИАТУРЫ -----------------
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Мужская одежда"), KeyboardButton("Женская одежда")],
        [KeyboardButton("Аксессуары"), KeyboardButton("Обувь")],
        [KeyboardButton("Прочее"), KeyboardButton("Смотреть ассортимент")],
        [KeyboardButton("Распродажа"), KeyboardButton("Моя корзина")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def accessories_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кошельки | Картхолдеры"), KeyboardButton("Ремни")],
        [KeyboardButton("Очки"), KeyboardButton("Прочее аксессуары")],
        [KeyboardButton("Назад в меню"), KeyboardButton("Моя корзина")],
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
    """Размеры: 34, 34.5, ..., 45.5, 46"""
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
    """Размерная сетка одежды XS–XXL."""
    sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    rows = [list(map(KeyboardButton, sizes))]
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ----------------- СОСТОЯНИЯ ДИАЛОГА -----------------
MAIN_MENU, MEN_MENU, WOMEN_MENU, SHOES_TYPE, SHOES_SIZE, ACCESSORIES_MENU = range(6)

# ----------------- КОРЗИНА -----------------
def get_cart(user_data: dict) -> List[Dict]:
    return user_data.setdefault("cart", [])


# ----------------- ХЕНДЛЕРЫ -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Вас приветствует StealthShopBot! Надеюсь, вы подберёте для себя что-то "
        "и останетесь довольны.\n\n"
        f"Наши отзывы: {REVIEWS_URL}\n"
        f"Наш весь каталог: {CATALOG_URL}\n"
        f"Наш Instagram: {INSTAGRAM_URL}\n\n"
        "Приятных покупок.\n\n"
        "Добро пожаловать в магазин.\n"
        "Выберите раздел:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    return MAIN_MENU


# ---------- ГЛОБАЛЬНЫЙ ХЕНДЛЕР ЧЕКАУТА ----------
async def checkout_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает текст, когда пользователь уже выбрал способ получения
    и бот ждёт от него данных.
    Работает ДО ConversationHandler (group=0).
    """
    state = context.user_data.get("checkout_state")
    if not state:
        return

    text = update.message.text.strip()
    user = update.effective_user

    if state == "wait_phone_meet":
        context.user_data["checkout_state"] = None
        contact_info = f"Телефон (личная встреча): {text}"
        await create_order(update, context, mode="Личная встреча (Минск)", contact_info=contact_info)
        logger.info("User %s finished checkout (meet)", user.id)
        # останавливаем дальнейшую обработку апдейта
        raise ApplicationHandlerStop()

    if state == "wait_post_data":
        context.user_data["checkout_state"] = None
        contact_info = f"Доставка почтой. Данные:\n{text}"
        await create_order(update, context, mode="Доставка почтой", contact_info=contact_info)
        logger.info("User %s finished checkout (post)", user.id)
        raise ApplicationHandlerStop()


# ---------- ГЛАВНОЕ МЕНЮ ----------
async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Мужская одежда":
        context.user_data["gender"] = "Муж"
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
        context.user_data["gender"] = "Жен"
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
        context.user_data["gender"] = None
        await update.message.reply_text(
            "Обувь. Выберите тип:", reply_markup=shoes_type_keyboard()
        )
        return SHOES_TYPE

    if text == "Аксессуары":
        await update.message.reply_text(
            "Аксессуары. Выберите подкатегорию:",
            reply_markup=accessories_menu_keyboard(),
        )
        return ACCESSORIES_MENU

    if text == "Прочее":
        products = filter_products(main_category="Прочее")
        if not products:
            await update.message.reply_text(
                "Товаров в разделе «Прочее» пока нет.",
                reply_markup=main_menu_keyboard(),
            )
            return MAIN_MENU
        await send_products(update, context, products)
        return MAIN_MENU

    if text == "Смотреть ассортимент":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Открыть каталог", url=CATALOG_URL)]]
        )
        await update.message.reply_text(
            "Полный каталог можно посмотреть здесь:",
            reply_markup=keyboard,
        )
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        await show_cart(update, context)
        return MAIN_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- МЕНЮ АКСЕССУАРОВ ----------
async def accessories_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Моя корзина":
        await show_cart(update, context)
        return ACCESSORIES_MENU

    if text in (
        "Кошельки | Картхолдеры",
        "Ремни",
        "Очки",
        "Прочее аксессуары",
    ):
        products = filter_products(
            main_category="Аксессуары",
            subcategory=text,
            gender=None,
        )
        if not products:
            await update.message.reply_text(
                "Товаров с такими параметрами пока нет.",
                reply_markup=accessories_menu_keyboard(),
            )
            return ACCESSORIES_MENU

        await send_products(update, context, products)
        return ACCESSORIES_MENU

    await update.message.reply_text(
        "Выберите пункт из списка.",
        reply_markup=accessories_menu_keyboard(),
    )
    return ACCESSORIES_MENU


# ---------- МУЖСКАЯ ОДЕЖДА ----------
async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "Муж"

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Моя корзина":
        await show_cart(update, context)
        return MEN_MENU

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
            size_group="Одежда",
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
        "Выберите пункт из списка.", reply_markup=clothes_size_keyboard()
    )
    return MEN_MENU


# ---------- ЖЕНСКАЯ ОДЕЖДА ----------
async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "Жен"

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Моя корзина":
        await show_cart(update, context)
        return WOMEN_MENU

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
            size_group="Одежда",
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
        "Выберите пункт из списка.", reply_markup=clothes_size_keyboard()
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

    if text == "Моя корзина":
        await show_cart(update, context)
        return SHOES_TYPE

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
        main_category="Обувь",
        subcategory=subcat,
        size_group="Обувь",
        size=text,
        gender=None,
    )

    if not products:
        await update.message.reply_text(
            "Товаров с такими параметрами пока нет.",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await send_products(update, context, products)
    return SHOES_SIZE


# ---------- ОТПРАВКА ТОВАРОВ ----------
async def send_products(
    update: Update, context: ContextTypes.DEFAULT_TYPE, products: List[Dict]
):
    """Показывает товары: описание + цена + размер (если есть) + фото."""
    chat_id = update.effective_chat.id

    for row in products:
        title = row.get("Title") or "Без названия"
        desc = row.get("Description") or ""
        cond = row.get("Condition") or ""
        size = (row.get("Size") or "").strip()
        price_raw = row.get("Price")
        price_text = format_price_byn(price_raw)
        quantity = row.get("Quantity")
        photo_id = row.get("Photo_url") or None
        row_id = row.get("ID")

        lines = [title, ""]
        if cond:
            lines.append(f"Состояние: {cond}")
        if size:
            lines.append(f"Размер: {size}")
        lines.append(f"Цена: {price_text}")
        if quantity not in (None, "", "None"):
            lines.append(f"В наличии: {quantity} шт.")
        if desc:
            lines.append("")
            lines.append(f"Описание: {desc}")

        text = "\n".join(lines)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Добавить в корзину", callback_data=f"add_to_cart:{row_id}")]]
        )

        if photo_id and str(photo_id).lower() != "none":
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=str(photo_id),
                caption=text,
                reply_markup=keyboard,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=keyboard
            )


# ---------- КОРЗИНА: ПОКАЗАТЬ ----------
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = get_cart(context.user_data)
    chat_id = update.effective_chat.id

    if not cart:
        await context.bot.send_message(chat_id=chat_id, text="Ваша корзина пока пустая.")
        return

    total = 0.0
    for item in cart:
        total += parse_price_to_float(item.get("Price"))

    for idx, item in enumerate(cart, start=1):
        title = item.get("Title") or "Без названия"
        size = (item.get("Size") or "").strip()
        price_text = format_price_byn(item.get("Price"))
        item_id = item.get("ID") or "-"
        text = f"{idx}. ID: {item_id}\n{title}"
        if size:
            text += f"\nРазмер: {size}"
        text += f"\nЦена: {price_text}"

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Удалить", callback_data=f"remove_from_cart:{idx-1}")]]
        )
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

    summary = f"Всего позиций: {len(cart)}\nИтого: {total:.2f} BYN"
    summary_keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Оформить заказ", callback_data="start_checkout")],
            [InlineKeyboardButton("Очистить корзину", callback_data="clear_cart")],
        ]
    )
    await context.bot.send_message(
        chat_id=chat_id, text=summary, reply_markup=summary_keyboard
    )


# ---------- СОЗДАНИЕ ЗАКАЗА ----------
async def create_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    contact_info: str,
):
    user = update.effective_user
    cart = get_cart(context.user_data)

    if not cart:
        await update.message.reply_text("Корзина пуста, оформлять нечего.")
        return

    total = 0.0
    lines = []
    for idx, item in enumerate(cart, start=1):
        title = item.get("Title") or "Без названия"
        size = (item.get("Size") or "").strip()
        price_raw = item.get("Price")
        price_text = format_price_byn(price_raw)
        total += parse_price_to_float(price_raw)
        item_id = item.get("ID") or "-"
        photo_id = item.get("Photo_url") or "-"
        line = f"{idx}. ID: {item_id} | {title}"
        if size:
            line += f" | размер: {size}"
        line += f" | цена: {price_text} | file_id: {photo_id}"
        lines.append(line)

    cart_text = "\n".join(lines)
    total_text = f"{total:.2f} BYN"

    await update.message.reply_text(
        "Спасибо! Ваш заказ принят.\n"
        "Мы свяжемся с вами в ближайшее время.",
        reply_markup=main_menu_keyboard(),
    )

    context.user_data["cart"] = []

    if ORDERS_CHANNEL_ID:
        username = f"@{user.username}" if user.username else "нет username"
        profile_link = f"tg://user?id={user.id}"

        order_text = (
            "💥 НОВЫЙ ЗАКАЗ\n\n"
            f"Покупатель: {username}\n"
            f"ID: {user.id}\n"
            f"Профиль: {profile_link}\n\n"
            f"Способ получения: {mode}\n"
            f"{contact_info}\n\n"
            f"Товары:\n{cart_text}\n\n"
            f"ИТОГО: {total_text}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Связаться с покупателем",
                        callback_data=f"order_status:contact:{user.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Аннулировать заказ",
                        callback_data=f"order_status:canceled:{user.id}",
                    )
                ],
            ]
        )

        await context.bot.send_message(
            chat_id=ORDERS_CHANNEL_ID, text=order_text, reply_markup=keyboard
        )
    else:
        logger.warning("ORDERS_CHANNEL_ID is not set – заказы никуда не отправляются.")


# ---------- CALLBACK ДЛЯ КОРЗИНЫ И ЗАКАЗОВ ----------
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_data = context.user_data

    if data.startswith("add_to_cart:"):
        row_id = norm(data.split(":", 1)[1])
        products = load_products()
        for row in products:
            if norm(row.get("ID")) == row_id:
                cart = get_cart(user_data)
                cart.append(row)
                await query.message.reply_text("Товар добавлен в корзину.")
                break
        else:
            await query.message.reply_text("Не удалось найти товар в каталоге.")
        return

    if data.startswith("remove_from_cart:"):
        try:
            index = int(data.split(":", 1)[1])
        except ValueError:
       
