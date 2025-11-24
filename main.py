import os
import json
from typing import List, Dict, Any, Optional

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

import gspread
from google.oauth2 import service_account

# ========= Настройки окружения =========

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

SERVICE_JSON = os.getenv("GOOGLE_SERVICE_JSON")
if not SERVICE_JSON:
    raise RuntimeError("GOOGLE_SERVICE_JSON is not set")

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
if not SHEET_ID:
    raise RuntimeError("GOOGLE_SHEET_ID is not set")

# ========= Подключение к Google Sheets =========

def _load_gspread_client() -> gspread.Client:
    # В переменной окружения хранится ВЕСЬ JSON как одна строка
    creds_dict = json.loads(SERVICE_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def _get_worksheet():
    client = _load_gspread_client()
    sh = client.open_by_key(SHEET_ID)
    # Первый лист (как у тебя — "Лист1")
    return sh.get_worksheet(0)


def norm(s: Any) -> str:
    """Нормализация строки для сравнения:
    - в строку
    - убираем пробелы по краям
    - в нижний регистр
    - запятую меняем на точку
    """
    return str(s).strip().lower().replace(",", ".")


def find_products(
    main_category: str,
    subcategory: Optional[str],
    size_group: Optional[str],
    size: Optional[str],
) -> List[Dict[str, Any]]:
    """Ищет товары в таблице по переданным параметрам.
    Пол (Gender) НЕ фильтруем, чтобы Unisex тоже находился.
    """
    ws = _get_worksheet()
    rows = ws.get_all_records()

    n_main = norm(main_category)
    n_sub = norm(subcategory) if subcategory else ""
    n_group = norm(size_group) if size_group else ""
    n_size = norm(size) if size else ""

    results = []
    for row in rows:
        # Ожидаем заголовки:
        # ID, Gender, Main_category, Subcategory, Size_group, Size,
        # Title, Description, Condition, Price, Photo_url
        if norm(row.get("Main_category", "")) != n_main:
            continue

        if n_sub and norm(row.get("Subcategory", "")) != n_sub:
            continue

        if n_group and norm(row.get("Size_group", "")) != n_group:
            continue

        if n_size and norm(row.get("Size", "")) != n_size:
            continue

        results.append(row)

    return results


# ========= Состояния диалога =========

(
    MAIN_MENU,
    MEN_MENU,
    WOMEN_MENU,
    SHOES_TYPE,
    SHOES_SIZE,
) = range(5)

# ========= Клавиатуры =========

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


def shoes_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    """Аккуратная сетка:
    сначала целые размеры, затем половинки.
    Все с точкой (36.5), как ты просил.
    """

    whole = ["34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"]
    halves = ["35.5", "36.5", "37.5", "38.5", "39.5", "40.5", "41.5", "42.5", "43.5", "44.5"]

    keyboard: List[List[KeyboardButton]] = []

    # Целые
    for i in range(0, len(whole), 4):
        keyboard.append([KeyboardButton(s) for s in whole[i:i+4]])

    # Половинки
    for i in range(0, len(halves), 4):
        keyboard.append([KeyboardButton(s) for s in halves[i:i+4]])

    keyboard.append([KeyboardButton("Назад к категориям")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ========= Вспомогательные функции =========

async def send_products_list(
    update: Update,
    products: List[Dict[str, Any]],
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Отправка найденных товаров.
    Всё в одном сообщении, как каталог, для упрощения.
    """
    if not products:
        await update.message.reply_text("Товаров с такими параметрами пока нет.")
        return

    lines = []
    for row in products:
        title = row.get("Title", "").strip()
        price = row.get("Price", "")
        size = row.get("Size", "")
        condition = row.get("Condition", "")
        desc = row.get("Description", "")
        pid = row.get("ID", "")

        line = f"ID: {pid}\nНазвание: {title}\nРазмер: {size}\nСостояние: {condition}\nЦена: {price}"
        if desc:
            line += f"\nОписание: {desc}"
        lines.append(line)

    text = "Найденные товары:\n\n" + "\n\n---\n\n".join(lines)
    await update.message.reply_text(text)


# ========= Обработчики =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в магазин.\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ----- Главное меню -----

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
        # Сбрасываем текущий выбор обуви
        context.user_data["shoes_type"] = None
        await update.message.reply_text(
            "Обувь. Выберите тип:",
            reply_markup=shoes_type_keyboard(),
        )
        return SHOES_TYPE

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров пока в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи пока в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        cart: List[Dict[str, Any]] = context.user_data.get("cart", [])
        if not cart:
            await update.message.reply_text("Корзина пока пустая.")
        else:
            lines = []
            for item in cart:
                lines.append(f"{item.get('Title', '')} — {item.get('Price', '')}")
            await update.message.reply_text("Ваша корзина:\n" + "\n".join(lines))
        return MAIN_MENU

    await update.message.reply_text(
        "Не понял команду. Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ----- Мужская / женская одежда (пока без каталога) -----

async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text("Этот раздел одежды пока без каталога товаров.")
    return MEN_MENU


async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text("Этот раздел одежды пока без каталога товаров.")
    return WOMEN_MENU


# ----- Обувь -----

async def shoes_type_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    # Запоминаем тип обуви (кроссовки, кеды, сланцы, ботинки)
    if text in ("Кроссовки", "Кеды", "Сланцы", "Ботинки"):
        context.user_data["shoes_type"] = text
        await update.message.reply_text(
            "Обувь. Выберите размер обуви:",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите тип обуви с клавиатуры.",
        reply_markup=shoes_type_keyboard(),
    )
    return SHOES_TYPE


async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к категориям":
        await update.message.reply_text(
            "Обувь. Выберите тип:",
            reply_markup=shoes_type_keyboard(),
        )
        return SHOES_TYPE

    shoes_type = context.user_data.get("shoes_type")
    if not shoes_type:
        # На всякий случай, если потеряли состояние
        await update.message.reply_text(
            "Сначала выберите тип обуви.",
            reply_markup=shoes_type_keyboard(),
        )
        return SHOES_TYPE

    # Проверяем, что пользователь нажал кнопку размера,
    # но не жестко (мазнул по клавиатуре — всё равно пробуем).
    size_str = text.strip().replace(",", ".")
    # Поисковый запрос в таблицу:
    # Main_category = "Обувь"
    # Subcategory = shoes_type (Кеды и т.п.)
    # Size_group = "Обувь" (мы так и заполнили в таблице)
    # Size = размер (строкой, 36.5 и т.п.)
    try:
        products = find_products(
            main_category="Обувь",
            subcategory=shoes_type,
            size_group="Обувь",
            size=size_str,
        )
    except Exception as e:
        # Если что-то пошло не так с гугл-таблицей
        await update.message.reply_text(f"Ошибка при чтении каталога: {e}")
        return SHOES_SIZE

    await send_products_list(update, products, context)
    # Остаёмся в выборе размера, чтобы можно было щёлкать другие размеры
    return SHOES_SIZE


# ========= Запуск приложения =========

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
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)

    # На будущее: если вернём inline-кнопку "Добавить в корзину" —
    # добавим CallbackQueryHandler здесь.

    app.run_polling()


if __name__ == "__main__":
    main()
