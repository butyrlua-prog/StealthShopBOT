import os
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Состояния
MAIN_MENU, MEN_MENU, WOMEN_MENU, SHOES_CATEGORY, SHOES_SIZE = range(5)


# ---------------------- КЛАВИАТУРЫ ----------------------

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


def shoes_category_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("Кроссовки"), KeyboardButton("Кеды")],
        [KeyboardButton("Сланцы"), KeyboardButton("Ботинки")],
        [KeyboardButton("Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def shoes_size_keyboard() -> ReplyKeyboardMarkup:
    sizes = []
    current = 34.0
    while current <= 46.0:
        sizes.append(str(current).rstrip(".0"))
        current += 0.5

    keyboard = []
    row = []
    for i, size in enumerate(sizes, start=1):
        row.append(KeyboardButton(size))
        if i % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("Назад к подкатегориям")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------------- ХЭНДЛЕРЫ ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
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

    if text == "Обувь":
        await update.message.reply_text(
            "Выберите категорию обуви:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY

    if text == "Аксессуары":
        await update.message.reply_text("Раздел аксессуаров в разработке.")
        return MAIN_MENU

    if text == "Распродажа":
        await update.message.reply_text("Раздел распродажи в разработке.")
        return MAIN_MENU

    if text == "Моя корзина":
        await update.message.reply_text("Корзина пока пустая.")
        return MAIN_MENU

    await update.message.reply_text(
        "Выберите пункт из меню.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


# ----------- Мужские -----------

async def men_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text("Данные подкатегории скоро появятся.")
    return MEN_MENU


# ----------- Женские -----------

async def women_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    await update.message.reply_text("Данные подкатегории скоро появятся.")
    return WOMEN_MENU


# ----------- ОБУВЬ: подкатегории -----------

async def shoes_category_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад в меню":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text in ["Кроссовки", "Кеды", "Сланцы", "Ботинки"]:
        context.user_data["selected_shoes_category"] = text
        await update.message.reply_text(
            f"Выберите размер ({text}):",
            reply_markup=shoes_size_keyboard(),
        )
        return SHOES_SIZE

    await update.message.reply_text(
        "Выберите подкатегорию:",
        reply_markup=shoes_category_keyboard(),
    )
    return SHOES_CATEGORY


# ----------- ОБУВЬ: размерная сетка -----------

async def shoes_size_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Назад к подкатегориям":
        await update.message.reply_text(
            "Выберите категорию обуви:",
            reply_markup=shoes_category_keyboard(),
        )
        return SHOES_CATEGORY

    # Проверяем, что это размер
    try:
        size = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Выберите размер.")
        return SHOES_SIZE

    category = context.user_data.get("selected_shoes_category", "Обувь")

    await update.message.reply_text(
        f"Товары категории '{category}' размера {text} появятся позже."
    )
    return SHOES_SIZE


# ---------------------- MAIN ----------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT, main_menu_router)],
            MEN_MENU: [MessageHandler(filters.TEXT, men_menu_router)],
            WOMEN_MENU: [MessageHandler(filters.TEXT, women_menu_router)],
            SHOES_CATEGORY: [MessageHandler(filters.TEXT, shoes_category_router)],
            SHOES_SIZE: [MessageHandler(filters.TEXT, shoes_size_router)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
