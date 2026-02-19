import asyncio
import os
import uuid
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Platega API
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET")
PLATEGA_BASE_URL = "https://app.platega.io"

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Путь к фото-пруфу
PHOTO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "перед покупкой.jpg")

# Хранилище активных платежей: {transaction_id: {"user_id": ..., "method": ...}}
pending_payments = {}

# Цена доступа
PRICE_RUB = 690

# Тексты для разделов
TEXTS = {
    "payment": """💳 <b>Оплата доступа</b>

Стоимость: <b>690 ₽</b>

Выберите удобный способ оплаты:""",

    "link": """🔗 <b>Получить ссылку</b>

После подтверждения оплаты ты получишь доступ к закрытому контенту.

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


# ==================== Platega API ====================

async def platega_create_payment(payment_method: int, amount: float, user_id: int) -> dict | None:
    """Создаёт платёж через Platega API и возвращает данные транзакции."""
    url = f"{PLATEGA_BASE_URL}/transaction/process"
    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "paymentMethod": payment_method,
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB",
        },
        "description": f"Доступ к архиву | user {user_id}",
        "payload": str(user_id),
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Платёж создан: {data}")
                    return data
                else:
                    text = await resp.text()
                    logger.error(f"Ошибка создания платежа: {resp.status} — {text}")
                    return None
    except Exception as e:
        logger.error(f"Ошибка запроса к Platega: {e}")
        return None


async def platega_check_status(transaction_id: str) -> dict | None:
    """Проверяет статус транзакции через Platega API."""
    url = f"{PLATEGA_BASE_URL}/transaction/{transaction_id}"
    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return None
    except Exception as e:
        logger.error(f"Ошибка проверки статуса: {e}")
        return None


async def poll_payment_status(transaction_id: str, user_id: int):
    """Фоновая задача: проверяет статус платежа каждые 15 секунд в течение 30 минут."""
    max_checks = 120  # 30 минут / 15 секунд
    for _ in range(max_checks):
        await asyncio.sleep(15)

        if transaction_id not in pending_payments:
            return  # Платёж уже обработан или отменён

        status_data = await platega_check_status(transaction_id)
        if not status_data:
            continue

        status = status_data.get("status", "")

        if status == "CONFIRMED":
            # Оплата успешна!
            pending_payments.pop(transaction_id, None)
            try:
                await bot.send_message(
                    user_id,
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    "Для получения доступа напиши 👉 @vippomosh\n"
                    "Ответ в течении 5 минут ❤️",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_keyboard(),
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            return

        elif status in ("CANCELED", "CHARGEBACKED"):
            # Платёж отменён
            pending_payments.pop(transaction_id, None)
            try:
                await bot.send_message(
                    user_id,
                    "❌ <b>Платёж отменён</b>\n\n"
                    "Если произошла ошибка, попробуйте оплатить заново.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_keyboard(),
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            return

    # Таймаут — платёж так и не был завершён
    pending_payments.pop(transaction_id, None)


# ==================== Клавиатуры ====================

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


def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП (QR-код)", callback_data="pay_sbp")],
        [InlineKeyboardButton(text="₿ Криптовалюта", callback_data="pay_crypto")],
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


# ==================== Приветственное сообщение ====================

WELCOME_TEXT = """✅ Встречайте обновленный архив!
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


# ==================== Обработчики ====================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    photo = FSInputFile(PHOTO_PATH)
    await message.answer_photo(
        photo=photo,
        caption="📸 Вот что ты получишь после покупки 👆",
        parse_mode=ParseMode.HTML
    )
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "payment")
async def show_payment(callback: CallbackQuery):
    """Показать выбор способа оплаты"""
    await callback.message.edit_text(
        TEXTS["payment"],
        reply_markup=get_payment_methods_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data == "pay_sbp")
async def process_pay_sbp(callback: CallbackQuery):
    """Оплата через СБП"""
    await callback.answer("⏳ Создаю платёж...")

    user_id = callback.from_user.id
    data = await platega_create_payment(
        payment_method=2,  # СБП QR
        amount=PRICE_RUB,
        user_id=user_id,
    )

    if not data or not data.get("redirect"):
        await callback.message.edit_text(
            "❌ <b>Ошибка создания платежа</b>\n\n"
            "Попробуйте позже или напишите @vippomosh",
            reply_markup=get_back_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    transaction_id = data["transactionId"]
    redirect_url = data["redirect"]

    # Сохраняем платёж
    pending_payments[transaction_id] = {
        "user_id": user_id,
        "method": "СБП",
    }

    # Отправляем ссылку на оплату
    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 690₽ (СБП)", url=redirect_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{transaction_id}")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back")]
    ])

    await callback.message.edit_text(
        "🏦 <b>Оплата через СБП (QR-код)</b>\n\n"
        f"💰 Сумма: <b>{PRICE_RUB} ₽</b>\n\n"
        "Нажмите кнопку ниже для перехода к оплате.\n"
        "После оплаты нажмите «Проверить оплату» или дождитесь автоматического уведомления.",
        reply_markup=pay_keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Запускаем фоновую проверку статуса
    asyncio.create_task(poll_payment_status(transaction_id, user_id))


@dp.callback_query(F.data == "pay_crypto")
async def process_pay_crypto(callback: CallbackQuery):
    """Оплата криптовалютой"""
    await callback.answer("⏳ Создаю платёж...")

    user_id = callback.from_user.id
    data = await platega_create_payment(
        payment_method=13,  # Криптовалюта
        amount=PRICE_RUB,
        user_id=user_id,
    )

    if not data or not data.get("redirect"):
        await callback.message.edit_text(
            "❌ <b>Ошибка создания платежа</b>\n\n"
            "Попробуйте позже или напишите @vippomosh",
            reply_markup=get_back_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    transaction_id = data["transactionId"]
    redirect_url = data["redirect"]

    # Сохраняем платёж
    pending_payments[transaction_id] = {
        "user_id": user_id,
        "method": "Крипто",
    }

    # Отправляем ссылку на оплату
    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₿ Оплатить 690₽ (Крипто)", url=redirect_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{transaction_id}")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back")]
    ])

    await callback.message.edit_text(
        "₿ <b>Оплата криптовалютой</b>\n\n"
        f"💰 Сумма: <b>{PRICE_RUB} ₽</b>\n"
        "Принимаем: BTC, ETH, USDT\n\n"
        "Нажмите кнопку ниже для перехода к оплате.\n"
        "После оплаты нажмите «Проверить оплату» или дождитесь автоматического уведомления.",
        reply_markup=pay_keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Запускаем фоновую проверку статуса
    asyncio.create_task(poll_payment_status(transaction_id, user_id))


@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery):
    """Ручная проверка статуса платежа"""
    transaction_id = callback.data.replace("check_", "")

    status_data = await platega_check_status(transaction_id)
    if not status_data:
        await callback.answer("⏳ Не удалось проверить. Попробуйте позже.", show_alert=True)
        return

    status = status_data.get("status", "")

    if status == "CONFIRMED":
        pending_payments.pop(transaction_id, None)
        await callback.message.edit_text(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            "Для получения доступа напиши 👉 @vippomosh\n"
            "Ответ в течении 5 минут ❤️",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard(),
        )
    elif status == "PENDING":
        await callback.answer("⏳ Оплата ещё не поступила. Подождите немного.", show_alert=True)
    elif status in ("CANCELED", "CHARGEBACKED"):
        pending_payments.pop(transaction_id, None)
        await callback.message.edit_text(
            "❌ <b>Платёж отменён</b>\n\n"
            "Попробуйте оплатить заново.",
            reply_markup=get_main_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.answer(f"Статус: {status}", show_alert=True)


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
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


async def main():
    """Запуск бота"""
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
