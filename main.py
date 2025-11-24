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

# Логин продавца, чтобы показывать покупателю (можно задать в Railway как OWNER_USERNAME)
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@ВАШ_ЛОГИН_ТГ")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

if not GOOGLE_SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

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
    Size, Title, Description, Condition, Price, Photo_url
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
    - запятую заменяем на точку
    """
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
    gender=None — пол не учитывается (например, обувь unisex).
    """
    products = load_products()
    result = []

    n_main = norm(main_category)
    n_sub = norm(subcategory)
    n_group = norm(size_group)
    n_size = norm(size)
    n_gender = norm(gender)

    for row in products:
        # Основная категория
        if n_main and norm(row.get("Main_category")) != n_main:
            continue

        # Пол: если указан Муж/Жен, пропускаем только совпадающие
        # либо Unisex. Для обуви gender=None — не фильтруем.
        row_gender = norm(row.get("Gender"))
        if n_gender:
            if row_gender not in (n_gender, "unisex", ""):
                continue

        # Подкатегория
        if n_sub and norm(row.get("Subcategory")) != n_sub:
            continue

        # Группа размеров (например, "Обувь", "Одежда")
        if n_group and norm(row.get("Size_group")) != n_group:
            continue

        # Конкретный размер (36 и 36.0, 36,5 и 36.5 будут совпадать)
        if n_size and norm(row.get("Size")) != n_size:
            continue

        result.append(row)

    return result


def chunk_list(lst: List[str], n: int) -> List[List[str]]:
    """Разбивает список на подсписки длины n."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


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
        [KeyboardButton("Оформить заказ")],
        [KeyboardButton("Удалить товар")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ----------------- СОСТОЯНИЯ ДИАЛОГА -----------------
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_TYPE,
    SHOES_SIZE,
    CART_MENU,
    DELETE_FROM_CART,
    CHECKOUT_CHOICE,
    MEET_PHONE,
    POST_DETAILS,
) = range(10)


# ----------------- КОРЗИНА -----------------
def get_cart(user_data: dict) -> List[Dict]:
    return user_data.setdefault("cart", [])


def format_cart_text(cart: List[Dict]) -> str:
    if not cart:
        return "Ваша корзина пока пустая."

    lines = []
    total = 0.0
    for idx, item in enumerate(cart, start=1):
        price_raw = item.get("Price") or 0
        try:
            price_val = float(str(price_raw).replace(",", "."))
        except ValueError:
            price_val = 0.0
        total += price_val
        title = item.get("Title") or "Без названия"
        lines.append(f"{idx}) {title} — {price_raw} BYN")

    text = "Ваша корзина:\n\n" + "\n".join(lines) + f"\n\nИтого: {total:.2f} BYN"
    return text


async def send_cart_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = get_cart(context.user_data)
    text_cart = format_cart_text(cart)
    if not cart:
        await update.message.reply_text(text_cart, reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text(text_cart, reply_markup=cart_menu_keyboard())


def build_order_text(
    cart: List[Dict],
    delivery_type: str,
    contact_text: str,
    user,
) -> str:
    lines = []
    total = 0.0
    for idx, item in enumerate(cart, start=1):
        price_raw = item.get("Price") or 0
        try:
            price_val = float(str(price_raw).replace(",", "."))
        except ValueError:
            price_val = 0.0
        total += price_val
        title = item.get("Title") or "Без названия"
        size = item.get("Size") or ""
        lines.append(f"{idx}) {title} — {price_raw} BYN (размер: {size})")

    user_username = f"@{user.username}" if user.username else "нет username"
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    text = (
        f"Тип доставки: {delivery_type}\n\n"
        f"Контактные данные, которые указал покупатель:\n{contact_text}\n\n"
        f"Товары в заказе:\n"
        + ("\n".join(lines) if lines else "нет товаров")
        + f"\n\nИтого: {total:.2f} BYN\n\n"
        f"Покупатель:\n"
        f"ID: {user.id}\n"
        f"Username: {user_username}\n"
        f"Имя: {user_name}"
    )
    return text


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
        # Для обуви gender не фильтруем
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
        await send_cart_state(update, context)
        return CART_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- МУЖСКАЯ ОДЕЖДА ----------
async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    gender = "Муж"

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

    # Выбор размера одежды
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

    # допустимые размеры
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
        gender=None,  # unisex тоже пройдут
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
            "Ваша корзина пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Удалить товар":
        await update.message.reply_text(
            "Отправьте номер товара, который нужно удалить (1, 2, 3 ...)."
        )
        return DELETE_FROM_CART

    if text == "Оформить заказ":
        await update.message.reply_text(
            "Выберите способ получения заказа:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton("Личная встреча (Минск)")],
                    [KeyboardButton("Доставка почтой")],
                    [KeyboardButton("Отмена оформления")],
                ],
                resize_keyboard=True,
            ),
        )
        return CHECKOUT_CHOICE

    # любое другое — просто повторяем корзину
    await send_cart_state(update, context)
    return CART_MENU


# ---------- КОРЗИНА: УДАЛЕНИЕ ----------
async def delete_from_cart_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = get_cart(context.user_data)
    text = update.message.text.strip()

    if not cart:
        await update.message.reply_text(
            "Корзина уже пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    try:
        idx = int(text)
    except ValueError:
        await update.message.reply_text("Нужно отправить номер товара (1, 2, 3 ...).")
        await send_cart_state(update, context)
        return CART_MENU

    if idx < 1 or idx > len(cart):
        await update.message.reply_text(
            "Неверный номер. Проверьте список и попробуйте снова."
        )
        await send_cart_state(update, context)
        return CART_MENU

    removed = cart.pop(idx - 1)
    title = removed.get("Title") or "Без названия"
    await update.message.reply_text(f'Товар "{title}" удалён из корзины.')

    if cart:
        await send_cart_state(update, context)
        return CART_MENU
    else:
        await update.message.reply_text(
            "Корзина пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU


# ---------- ОФОРМЛЕНИЕ: ВЫБОР СПОСОБА ----------
async def checkout_choice_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    cart = get_cart(context.user_data)

    if not cart:
        await update.message.reply_text(
            "Ваша корзина пустая.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Отмена оформления":
        await update.message.reply_text(
            "Оформление заказа отменено.", reply_markup=main_menu_keyboard()
        )
        return MAIN_MENU

    if text == "Личная встреча (Минск)":
        await update.message.reply_text(
            "Напишите одним сообщением номер телефона для связи."
        )
        return MEET_PHONE

    if text == "Доставка почтой":
        await update.message.reply_text(
            "Напишите одним сообщением: ФИО, номер телефона, город и адрес/индекс "
            "или номер отделения (если это европочта)."
        )
        return POST_DETAILS

    await update.message.reply_text(
        "Выберите вариант: «Личная встреча (Минск)», «Доставка почтой» "
        "или «Отмена оформления»."
    )
    return CHECKOUT_CHOICE


# ---------- ОФОРМЛЕНИЕ: ЛИЧНАЯ ВСТРЕЧА ----------
async def meet_phone_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_text = update.message.text.strip()
    user = update.effective_user
    cart = get_cart(context.user_data)

    order_text = build_order_text(
        cart=cart,
        delivery_type="Личная встреча (Минск)",
        contact_text=phone_text,
        user=user,
    )

    await update.message.reply_text(
        "Спасибо! Ваш заказ оформлен.\n\n"
        + order_text
        + f"\n\nДля связи с продавцом: {OWNER_USERNAME}",
        reply_markup=main_menu_keyboard(),
    )

    cart.clear()
    return MAIN_MENU


# ---------- ОФОРМЛЕНИЕ: ДОСТАВКА ПОЧТОЙ ----------
async def post_details_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details_text = update.message.text.strip()
    user = update.effective_user
    cart = get_cart(context.user_data)

    order_text = build_order_text(
        cart=cart,
        delivery_type="Доставка почтой",
        contact_text=details_text,
        user=user,
    )

    await update.message.reply_text(
        "Спасибо! Ваш заказ оформлен.\n\n"
        + order_text
        + f"\n\nДля связи с продавцом: {OWNER_USERNAME}",
        reply_markup=main_menu_keyboard(),
    )

    cart.clear()
    return MAIN_MENU


# ---------- ОТПРАВКА ТОВАРОВ ----------
async def send_products(
    update: Update, context: ContextTypes.DEFAULT_TYPE, products: List[Dict]
):
    """
    Показывает товары: описание + цена (с BYN) + размер + фото + кнопка "Добавить в корзину"
    """
    chat_id = update.effective_chat.id

    for row in products:
        title = row.get("Title") or "Без названия"
        desc = row.get("Description") or ""
        cond = row.get("Condition") or ""
        size = row.get("Size") or ""
        price = row.get("Price") or ""
        photo_url = row.get("Photo_url") or None
        row_id = row.get("ID")

        if price != "":
            price_display = f"{price} BYN"
        else:
            price_display = "—"

        text = (
            f"{title}\n\n"
            f"Состояние: {cond}\n"
            f"Размер: {size}\n"
            f"Цена: {price_display}"
        )
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
                chat_id=chat_id, text=text, reply_markup=keyboard
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
            DELETE_FROM_CART: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_from_cart_router)
            ],
            CHECKOUT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_choice_router)
            ],
            MEET_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, meet_phone_router)
            ],
            POST_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_details_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
