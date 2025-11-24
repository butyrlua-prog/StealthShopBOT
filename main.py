import os
import json
import logging
from typing import Dict, Any, List

import gspread
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

# ---------------------- ЛОГИ ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------- ENV ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
if not SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

# ---------------------- GOOGLE SHEETS ----------------------
creds_dict = json.loads(SERVICE_JSON)
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_key(SHEET_ID).sheet1  # первый лист


def load_items(
    main_category: str,
    subcategory: str | None = None,
    size_group: str | None = None,
    size: str | None = None,
) -> List[Dict[str, Any]]:
    """Фильтрация строк из таблицы под выбранный фильтр."""
    records = sheet.get_all_records()

    result: List[Dict[str, Any]] = []
    for row in records:
        if not row.get("Main_category"):
            continue

        if row.get("Main_category") != main_category:
            continue
        if subcategory and row.get("Subcategory") != subcategory:
            continue
        if size_group and row.get("Size_group") != size_group:
            continue
        if size and str(row.get("Size")) != str(size):
            continue

        result.append(row)
    return result


# ---------------------- СОСТОЯНИЯ ----------------------
(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_MENU,
    CATEGORY_SIZE,      # выбор размера для одежды/обуви
    MEN_OUTER_TYPE,
    WOMEN_OUTER_TYPE,
) = range(7)

# ---------------------- КЛАВИАТУРЫ ----------------------
CLOTHES_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]  # БЕЗ XXXL
SHOES_SIZES = [
    "34", "34.5",
    "35", "35.5",
    "36", "36.5",
    "37", "37.5",
    "38", "38.5",
    "39", "39.5",
    "40", "40.5",
    "41", "41.5",
    "42", "42.5",
    "43", "43.5",
    "44", "44.5",
    "45", "45.5",
    "46",
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Мужская одежда"), KeyboardButton("Женская одежда")],
        [KeyboardButton("Обувь"), KeyboardButton("Аксессуары")],
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


def shoes_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def clothes_size_keyboard() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for s in CLOTHES_SIZES:
        row.append(KeyboardButton(s))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for s in SHOES_SIZES:
        row.append(KeyboardButton(s))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton("Назад к категориям")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def men_outer_type_keyboard() -> ReplyKeyboardMarkup:
    # БЕЗ "(муж)"
    keyboard = [
        [KeyboardButton("Куртки | Плащи | Ветровки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Бомберы | Свитеры")],
        [KeyboardButton("Назад к мужской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def women_outer_type_keyboard() -> ReplyKeyboardMarkup:
    # БЕЗ "(жен)"
    keyboard = [
        [KeyboardButton("Куртки")],
        [KeyboardButton("Худи | Свитшоты | Олимпийки")],
        [KeyboardButton("Свитеры | Бомберы")],
        [KeyboardButton("Назад к женской одежде")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------------- ПОМОЩНИКИ ----------------------
async def show_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    items: List[Dict[str, Any]],
) -> None:
    if not items:
        await update.message.reply_text("По выбранным параметрам сейчас ничего нет.")
        return

    user_cart = context.user_data.setdefault("cart", [])

    for item in items:
        title = item.get("Title", "")
        size = item.get("Size", "")
        price = item.get("Price", "")
        desc = item.get("Description", "")
        condition = item.get("Condition", "")
        photo_url = item.get("Photo_url", "")
        item_id = item.get("ID")

        text = (
            f"{title}\n"
            f"Размер: {size}\n"
            f"Состояние: {condition}\n"
            f"Цена: {price}\n"
            f"Описание: {desc}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Добавить в корзину",
                        callback_data=f"add_to_cart:{item_id}",
                    )
                ]
            ]
        )

        if photo_url and str(photo_url).lower() not in ("none", ""):
            await update.message.reply_photo(
                photo=photo_url,
                caption=text,
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)


# ---------------------- ОБРАБОТЧИКИ ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("cart", [])
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- ГЛАВНОЕ МЕНЮ ----------
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

    if text == "Обувь":
        await update.message.reply_text(
            "Раздел обуви. Выберите подкатегорию:",
            reply_markup=shoes_menu_keyboard(),
        )
        return SHOES_MENU

    if text == "Аксессуары":
        await update.message.reply_text("Аксессуары пока в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        cart: list[Dict[str, Any]] = context.user_data.get("cart", [])
        if not cart:
            await update.message.reply_text("Корзина пуста.")
        else:
            lines = []
            for i, item in enumerate(cart, start=1):
                lines.append(f"{i}. {item.get('Title', '')} — {item.get('Price', '')}")
            await update.message.reply_text("\n".join(lines))
        return MAIN_MENU

    await update.message.reply_text(
        "Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ---------- МУЖСКАЯ ОДЕЖДА ----------
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
            reply_markup=men_outer_type_keyboard(),
        )
        return MEN_OUTER_TYPE

    # остальные подкатегории одежды для мужчин
    # (пока просто заглушки без каталога)
    await update.message.reply_text("Раздел пока в разработке.")
    return MEN_MENU


async def men_outer_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к мужской одежде":
        await update.message.reply_text(
            "Мужская одежда. Выберите подкатегорию:",
            reply_markup=men_menu_keyboard(),
        )
        return MEN_MENU

    # Сохраняем фильтр для таблицы под верхнюю одежду (муж)
    context.user_data["pending_filters"] = {
        "main_category": "Мужская одежда",
        "subcategory": text,       # тип верхней одежды
        "size_group": "Одежда",
    }

    await update.message.reply_text(
        "Выберите размер:",
        reply_markup=clothes_size_keyboard(),
    )
    return CATEGORY_SIZE


# ---------- ЖЕНСКАЯ ОДЕЖДА ----------
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
            reply_markup=women_outer_type_keyboard(),
        )
        return WOMEN_OUTER_TYPE

    await update.message.reply_text("Раздел пока в разработке.")
    return WOMEN_MENU


async def women_outer_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к женской одежде":
        await update.message.reply_text(
            "Женская одежда. Выберите подкатегорию:",
            reply_markup=women_menu_keyboard(),
        )
        return WOMEN_MENU

    context.user_data["pending_filters"] = {
        "main_category": "Женская одежда",
        "subcategory": text,
        "size_group": "Одежда",
    }

    await update.message.reply_text(
        "Выберите размер:",
        reply_markup=clothes_size_keyboard(),
    )
    return CATEGORY_SIZE


# ---------- ОБУВЬ ----------
async def shoes_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in ("Кроссовки", "Кеды", "Сланцы", "Ботинки"):
        # Для обуви гендер не фильтруем, только main/sub/size_group
        context.user_data["pending_filters"] = {
            "main_category": "Обувь",
            "subcategory": text,
            "size_group": "Обувь",
        }
        await update.message.reply_text(
            "Выберите размер обуви:",
            reply_markup=shoes_size_keyboard(),
        )
        return CATEGORY_SIZE

    await update.message.reply_text(
        "Выберите подкатегорию обуви из списка.",
        reply_markup=shoes_menu_keyboard(),
    )
    return SHOES_MENU


# ---------- ВЫБОР РАЗМЕРА (ОБЩИЙ) ----------
async def size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        # Возвращаемся туда, откуда пришли
        filters_data = context.user_data.get("pending_filters", {})
        main_cat = filters_data.get("main_category", "")

        if main_cat == "Обувь":
            await update.message.reply_text(
                "Раздел обуви. Выберите подкатегорию:",
                reply_markup=shoes_menu_keyboard(),
            )
            return SHOES_MENU

        if main_cat == "Мужская одежда":
            await update.message.reply_text(
                "Мужская верхняя одежда. Выберите тип:",
                reply_markup=men_outer_type_keyboard(),
            )
            return MEN_OUTER_TYPE

        if main_cat == "Женская одежда":
            await update.message.reply_text(
                "Женская верхняя одежда. Выберите тип:",
                reply_markup=women_outer_type_keyboard(),
            )
            return WOMEN_OUTER_TYPE

        # запасной вариант
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    # обычный выбор размера
    filters_data = context.user_data.get("pending_filters")
    if not filters_data:
        await update.message.reply_text(
            "Что-то пошло не так, возвращаю в меню.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    main_category = filters_data["main_category"]
    subcategory = filters_data.get("subcategory")
    size_group = filters_data.get("size_group")

    items = load_items(
        main_category=main_category,
        subcategory=subcategory,
        size_group=size_group,
        size=text,
    )

    await show_items(update, context, items)
    return CATEGORY_SIZE


# ---------- CALLBACK ДЛЯ КОРЗИНЫ ----------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith("add_to_cart:"):
        item_id = data.split(":", maxsplit=1)[1]
        records = sheet.get_all_records()
        for row in records:
            if str(row.get("ID")) == str(item_id):
                cart = context.user_data.setdefault("cart", [])
                cart.append(row)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text("Товар добавлен в корзину.")
                break


# ---------- ОСНОВНОЙ MAIN ----------
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
            MEN_OUTER_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, men_outer_type_router)
            ],
            WOMEN_OUTER_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, women_outer_type_router)
            ],
            CATEGORY_SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, size_router)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(callback_router))

    app.run_polling()


if __name__ == "__main__":
    main()
