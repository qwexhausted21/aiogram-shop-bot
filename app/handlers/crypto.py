import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiosend import CryptoPay, PollingRouter
from aiosend.types import Invoice

from app import database as db
from app.config import CRYPTO_PAY_TOKEN, CRYPTO_PAY_ENABLED

# Роутер aiogram для обработки нажатия на кнопку «Оплатить криптой»
router = Router()

cp = None
if CRYPTO_PAY_ENABLED and CRYPTO_PAY_TOKEN:
    cp = CryptoPay(token=CRYPTO_PAY_TOKEN)

# Создаём PollingRouter для событий CryptoPay
polling_router = PollingRouter(name=__name__)


@polling_router.invoice_paid()
async def on_crypto_paid(invoice: Invoice):
    """Срабатывает, когда счёт CryptoPay переходит в статус «оплачен»."""
    user_id = int(invoice.payload) if invoice.payload else None
    if not user_id:
        logging.warning("CryptoPay: в счёте отсутствует payload (user_id)")
        return

    amount_rub = invoice.amount
    await db.update_balance(user_id, amount_rub)

    try:
        from app.main_state import bot
        if bot:
            await bot.send_message(
                user_id,
                f"✅ Оплата криптовалютой прошла успешно!\nЗачислено: {amount_rub:.0f} ₽"
            )
    except Exception as e:
        logging.warning(f"Не удалось уведомить пользователя {user_id}: {e}")


# Подключаем polling_router к корневому роутеру CryptoPay
if cp:
    cp.include_router(polling_router)


@router.callback_query(F.data.startswith("pay_crypto_"))
async def process_crypto_payment(callback: CallbackQuery):
    if not cp:
        await callback.answer("Оплата криптовалютой временно недоступна.", show_alert=True)
        return

    amount = float(callback.data.split("_")[2])
    user_id = callback.from_user.id

    try:
        invoice = await cp.create_invoice(
            amount=amount,
            currency_type="fiat",  # 👈 тип цены — фиатная
            fiat="RUB",            # 👈 код валюты
            description=f"Пополнение баланса на {amount} ₽",
            payload=str(user_id)
        )

        await callback.message.answer(
            f"💰 Для оплаты {amount:.0f} ₽ перейдите по ссылке:\n{invoice.bot_invoice_url}",
            disable_web_page_preview=True
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"CryptoPay error при создании счёта: {e}")
        await callback.answer("Ошибка при создании счёта.", show_alert=True)