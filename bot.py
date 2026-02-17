import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота (вставь свой токен в файл .env)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Путь к фото-пруфу
PHOTO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Прикрепи фото.jpg")

# Тексты для разделов (настрой под себя)
TEXTS = {
    "payment": """💳 <b>Оплата доступа</b>

Стоимость: <b>XXX руб.</b>

Способы оплаты:
• Карта Сбербанк: 0000 0000 0000 0000
• СБП: +7 (XXX) XXX-XX-XX

После оплаты отправь скриншот @username""",

    "link": """🔗 <b>Получить ссылку</b>

После подтверждения оплаты ты получишь ссылку на закрытый канал/папку с контентом.

Если ты уже оплатил, напиши @vippomosh для получения доступа.""",

    "reviews": """⭐ <b>Отзывы покупателей</b>

✅ "Всё супер, контент огонь!"
✅ "Быстро получил доступ, рекомендую"
✅ "Отличное качество видео"

📌 Больше отзывов: @vippomosh""",

    "info": """ℹ️ <b>Информация</b>

💡 <b>Помощь и контакты</b>
Если есть вопросы — пишите @vippomosh"""
}


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data="payment")],
        [InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="link")],
        [InlineKeyboardButton(text="⭐ Отзывы покупателей", callback_data="reviews")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ])
    return keyboard


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back")]
    ])
    return keyboard


def get_info_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела Информация"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-02-07-55")],
        [InlineKeyboardButton(text="📜 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-02-07-19")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back")]
    ])
    return keyboard


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name or "друг"

    welcome_text = f"""✅ Встречайте обновленный архив!
Мы провели титаническую работу, чтобы вы получали только кайф:

🔥 150 000 — идеально отфильтрованных видео (никакого мусора!)
😈 Удобство — всё открывается и качается с любого телефона/ПК
🔥 Безопасность — мгновенное восстановление при блокировке
✅ База данных — закрытые источники (Darknet, Onion, Mail, Я.Диск)
🔥 Монополия — мы скупили контент конкурентов + другие приватки

💸 Главный козырь — ЦЕНА!
Самые низкие цены и лучшее качество на рынке.

⏰ ВСЕГО 690 РУБЛЕЙ
Это дешевле, чем сходить в кино, а удовольствия — на годы вперёд! 🎬🚫
Никакой ежемесячной подписки. Платишь один раз — пользуешься всегда.

💣 Пока думаешь — кто-то другой уже смотрит.
Жми кнопку и забирай вечный доступ за 690₽, пока цена не выросла!

👇 Хочу доступ за 690₽! 👇"""

    photo = FSInputFile(PHOTO_PATH)
    await message.answer_photo(
        photo=photo,
        caption="📸 Вот что ты получишь после покупки 👆",
        parse_mode=ParseMode.HTML
    )
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "payment")
async def show_payment(callback: CallbackQuery):
    """Показать информацию об оплате"""
    await callback.message.edit_text(
        TEXTS["payment"],
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "link")
async def show_link(callback: CallbackQuery):
    """Показать информацию о получении ссылки"""
    await callback.message.edit_text(
        TEXTS["link"],
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "reviews")
async def show_reviews(callback: CallbackQuery):
    """Показать отзывы"""
    await callback.message.edit_text(
        TEXTS["reviews"],
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    """Показать информацию"""
    await callback.message.edit_text(
        TEXTS["info"],
        reply_markup=get_info_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery):
    """Вернуться в главное меню"""
    user_name = callback.from_user.first_name or "друг"

    welcome_text = f"""✅ Встречайте обновленный архив!
Мы провели титаническую работу, чтобы вы получали только кайф:

🔥 150 000 — идеально отфильтрованных видео (никакого мусора!)
😈 Удобство — всё открывается и качается с любого телефона/ПК
🔥 Безопасность — мгновенное восстановление при блокировке
✅ База данных — закрытые источники (Darknet, Onion, Mail, Я.Диск)
🔥 Монополия — мы скупили контент конкурентов + другие приватки

💸 Главный козырь — ЦЕНА!
Самые низкие цены и лучшее качество на рынке.

⏰ ВСЕГО 690 РУБЛЕЙ
Это дешевле, чем сходить в кино, а удовольствия — на годы вперёд! 🎬🚫
Никакой ежемесячной подписки. Платишь один раз — пользуешься всегда.

💣 Пока думаешь — кто-то другой уже смотрит.
Жми кнопку и забирай вечный доступ за 690₽, пока цена не выросла!

👇 Хочу доступ за 690₽! 👇"""

    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


async def main():
    """Запуск бота"""
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
