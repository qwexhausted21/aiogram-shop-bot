import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import database as db
from app.config import MANUAL_PAYMENT_PHONE, MANUAL_PAYMENT_ENABLED, ADMIN_IDS

router = Router()


@router.callback_query(F.data.startswith("pay_manual_"))
async def process_manual_payment(callback: CallbackQuery):
    if not MANUAL_PAYMENT_ENABLED:
        await callback.answer("Ручной перевод временно недоступен.", show_alert=True)
        return

    amount = float(callback.data.split("_")[2])
    user_id = callback.from_user.id

    payment_id = await db.create_manual_payment(user_id, amount)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил", callback_data=f"confirm_manual_{payment_id}")

    await callback.message.answer(
        f"💸 **Оплата переводом**\n\n"
        f"1. Переведите **{amount:.0f} ₽** по номеру телефона: `{MANUAL_PAYMENT_PHONE}` (СБП)\n"
        f"2. В комментарии к переводу укажите: `Оплата за бота`\n"
        f"3. После перевода нажмите кнопку ниже.\n\n"
        f"⚠️ Администратор проверит перевод и зачислит баланс вручную.",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_manual_"))
async def confirm_manual_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[2])
    user = callback.from_user
    
    # Получаем данные о заявке из БД
    payment = await db.get_manual_payment_by_id(payment_id)
    if not payment or payment[3] != 'pending':
        await callback.message.edit_text("❌ Заявка уже обработана или не найдена.")
        await callback.answer()
        return
        
    amount = payment[2]
    user_name = user.full_name or user.username or f"id{user.id}"

    # Формируем уведомление для админов
    admin_text = (
        f"🔔 <b>Новая заявка на оплату СБП!</b>\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID пользователя: <code>{user.id}</code>\n"
        f"💰 Сумма: <b>{amount:.0f} ₽</b>\n"
        f"📝 Номер заявки: <code>{payment_id}</code>\n\n"
        f"Проверьте перевод и подтвердите зачисление."
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_manual_{payment_id}")

    # Рассылаем уведомление всем админам
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id, 
                admin_text, 
                reply_markup=kb.as_markup(), 
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"Не удалось уведомить админа {admin_id}: {e}")

    await callback.message.edit_text(
        "✅ Заявка отправлена на проверку администратору.\n"
        "Ожидайте подтверждения, баланс пополнится автоматически."
    )
    await callback.answer("Заявка отправлена!")