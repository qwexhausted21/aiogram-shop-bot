"""
Обработчики для обычных пользователей.
"""
import logging
import html
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app import database as db
from app.config import (
    ADMIN_IDS, DEBUG_MODE, REFERRAL_DISCOUNT_PERCENT, IMAGES_DIR,
    CRYPTO_PAY_ENABLED, MANUAL_PAYMENT_ENABLED,
    PAYMENTS_ENABLED, PLATEGA_ENABLED
)
from app.payments import create_payment_link, generate_order_id
from app.keyboards import (
    main_menu, back_to_menu_keyboard, courses_keyboard,
    course_details_keyboard, profile_keyboard,
    payment_keyboard, buy_confirm_keyboard,
)
from app.tracker import track, cleanup, cleanup_by_message

router = Router()


class TopUpState(StatesGroup):
    waiting_for_amount = State()


async def send_tracked(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    msg = await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    track(callback.from_user.id, msg.message_id)
    return msg


# --- /start -----------------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await cleanup_by_message(message)
    await state.clear()

    user = message.from_user
    referrer_id = None
    if message.text and " " in message.text:
        payload = message.text.split(maxsplit=1)[1]
        if payload.startswith("ref_"):
            try:
                referrer_id = int(payload[4:])
            except ValueError:
                pass

    is_new_user = not await db.get_user(user.id)
    if is_new_user:
        await db.create_user(user.id, user.username or "", referrer_id=referrer_id)

        # Если пришёл по реферальной ссылке — уведомляем реферера
        if referrer_id:
            name = user.full_name or user.username or f"id{user.id}"
            try:
                await message.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"👋 <b>По твоей ссылке перешёл новый пользователь:</b> {name}\n\n"
                        f"Когда он купит любой курс, ты получишь "
                        f"<b>скидку {REFERRAL_DISCOUNT_PERCENT:.0f}%</b> на следующую покупку."
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logging.warning(f"Не удалось уведомить реферера {referrer_id}: {e}")

    is_admin = user.id in ADMIN_IDS
    text = (
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Здесь ты можешь купить полезные онлайн-курсы.\n"
        "Выбирай кнопку ниже, чтобы начать."
    )
    if DEBUG_MODE:
        text += "\n\n🧪 <i>РЕЖИМ ОТЛАДКИ — реальные платежи отключены</i>"

    photo_path = Path(IMAGES_DIR) / "welcome.jpg"
    if photo_path.exists():
        try:
            msg = await message.answer_photo(
                photo=FSInputFile(photo_path), caption=text,
                reply_markup=main_menu(is_admin=is_admin), parse_mode="HTML",
            )
            track(user.id, msg.message_id)
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить welcome-фото: {e}")

    msg = await message.answer(text, reply_markup=main_menu(is_admin=is_admin), parse_mode="HTML")
    track(user.id, msg.message_id)


# --- Главное меню -----------------------------------------------------------
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    text = "👋 <b>Главное меню</b>\n\nВыбери действие:"
    if DEBUG_MODE:
        text += "\n\n🧪 <i>РЕЖИМ ОТЛАДКИ</i>"

    photo_path = Path(IMAGES_DIR) / "welcome.jpg"
    if photo_path.exists():
        try:
            msg = await callback.message.answer_photo(
                photo=FSInputFile(photo_path), caption=text,
                reply_markup=main_menu(is_admin=is_admin), parse_mode="HTML",
            )
            track(callback.from_user.id, msg.message_id)
            await callback.answer()
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить welcome-фото: {e}")

    await send_tracked(callback, text, reply_markup=main_menu(is_admin=is_admin))
    await callback.answer()


# --- Купить курсы -----------------------------------------------------------
@router.callback_query(F.data == "menu_buy")
async def show_courses(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()

    courses = await db.get_visible_courses()
    if not courses:
        text = "📚 Пока нет доступных курсов. Загляни позже!"
        kb = back_to_menu_keyboard()
    else:
        text = f"📚 <b>Доступные курсы</b>\n\nВсего: {len(courses)}. Нажми на курс, чтобы узнать подробности:"
        kb = courses_keyboard(courses)

    photo_path = Path(IMAGES_DIR) / "buy.jpg"
    if photo_path.exists():
        try:
            m = await callback.message.answer_photo(
                photo=FSInputFile(photo_path), caption=text,
                reply_markup=kb, parse_mode="HTML",
            )
            track(callback.from_user.id, m.message_id)
            await callback.answer()
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить buy-фото: {e}")

    await send_tracked(callback, text, reply_markup=kb)
    await callback.answer()


# --- Детали курса -----------------------------------------------------------
@router.callback_query(F.data.startswith("course_"))
async def show_course_details(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()

    course_id = int(callback.data.split("_")[1])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    _, title, description, price, channel_link, cover, hidden = course
    text = f"<b>{title}</b>\n\n{description}\n\n💰 Цена: <b>{price:.0f} ₽</b>"
    kb = course_details_keyboard(course_id, price)

    if cover:
        try:
            m = await callback.message.answer_photo(
                photo=cover, caption=text, reply_markup=kb, parse_mode="HTML",
            )
            track(callback.from_user.id, m.message_id)
            await callback.answer()
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить обложку курса: {e}")

    await send_tracked(callback, text, reply_markup=kb)
    await callback.answer()


# --- Покупка курса ----------------------------------------------------------
@router.callback_query(F.data.startswith("buy_"))
async def process_buy_course(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await cleanup(callback)
    await state.clear()

    course_id = int(callback.data.split("_")[1])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    _, title, description, price, channel_link, cover, hidden = course
    balance = await db.get_balance(user_id)
    discounts = await db.get_user_discounts(user_id)

    if discounts > 0:
        final_price = round(price * (1 - REFERRAL_DISCOUNT_PERCENT / 100))
        text = (
            f"<b>{title}</b>\n\n"
            f"💰 Обычная цена: <s>{price:.0f} ₽</s>\n"
            f"🎁 Цена со скидкой {REFERRAL_DISCOUNT_PERCENT:.0f}%: <b>{final_price:.0f} ₽</b>\n"
            f"💳 Твой баланс: <b>{balance:.0f} ₽</b>\n\n"
        )
    else:
        final_price = price
        text = (
            f"<b>{title}</b>\n\n"
            f"💰 Цена: <b>{price:.0f} ₽</b>\n"
            f"💳 Твой баланс: <b>{balance:.0f} ₽</b>\n\n"
        )

    if balance >= final_price:
        text += "✅ Ты можешь купить прямо сейчас!"
        await send_tracked(callback, text, reply_markup=buy_confirm_keyboard(course_id, final_price))
    else:
        need = final_price - balance
        text += f"❌ Не хватает <b>{need:.0f} ₽</b>.\nПополни баланс и возвращайся!"
        await send_tracked(callback, text, reply_markup=payment_keyboard(need))

    


@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_purchase(callback: CallbackQuery, state: FSMContext):

    await callback.answer("Покупка совершена!")
    await cleanup(callback)
    await state.clear()

    

    course_id = int(callback.data.split("_")[2])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    _, title, description, price, channel_link, cover, hidden = course

    discounts = await db.get_user_discounts(user_id)
    if discounts > 0:
        final_price = round(price * (1 - REFERRAL_DISCOUNT_PERCENT / 100))
        used_discount = True
    else:
        final_price = price
        used_discount = False

    balance = await db.get_balance(user_id)
    if balance < final_price:
        await callback.answer("Недостаточно средств", show_alert=True)
        return

    await db.update_balance(user_id, -final_price)
    if used_discount:
        await db.use_discount(user_id)
    await db.add_purchase(user_id, course_id, final_price)

    # Реферальная логика
    user_row = await db.get_user(user_id)
    if user_row and user_row[3]:
        referrer_id = user_row[3]
        already_counted = await db.is_ref_counted(user_id)
        if not already_counted:
            await db.mark_ref_counted(user_id)
            await db.add_discount(referrer_id)

            name = callback.from_user.full_name or callback.from_user.username or f"id{user_id}"
            try:
                await callback.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"🎉 <b>Твой реферал купил курс!</b>\n\n"
                        f"Пользователь: <b>{name}</b>\n"
                        f"Курс: <b>{title}</b>\n\n"
                        f"Ты получил <b>скидку {REFERRAL_DISCOUNT_PERCENT:.0f}%</b> "
                        f"на следующую покупку.\n"
                        f"Она применится автоматически при оформлении."
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logging.warning(f"Не удалось уведомить реферера {referrer_id}: {e}")

        # --- Выдаём ссылку на материалы ---
    link = await get_course_invite_link(callback.bot, course, user_id)
    logging.info(f"DEBUG: Ссылка для курса {course_id}: {link!r}")  # Выведет ссылку в консоль

    discount_line = ""
    if used_discount:
        discount_line = f"🎁 Применена скидка {REFERRAL_DISCOUNT_PERCENT:.0f}%\n"

    # Если ссылка есть, делаем её красивой кнопкой/текстом
    if link and link.startswith("http"):
        import html
        # Формируем надежную ссылку, чтобы Telegram её точно не сломал
        link_text = f'<a href="{html.escape(link)}">Нажми сюда, чтобы открыть материалы</a>'
    else:
        link_text = "⚠️ Ссылка на материалы временно недоступна. Свяжитесь с поддержкой."

    await send_tracked(
        callback,
        f"🎉 <b>Покупка успешна!</b>\n\n"
        f"Курс: <b>{title}</b>\n"
        f"{discount_line}"
        f"Списано: <b>{final_price:.0f} ₽</b>\n\n"
        f"🔗 <b>Доступ к материалам:</b>\n{link_text}\n\n"
        f"⚠️ Ссылка персональная — не передавай её третьим лицам.",
        reply_markup=back_to_menu_keyboard(),
    )
# --- Личный кабинет ---------------------------------------------------------
@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()

    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала нажми /start", show_alert=True)
        return

    balance = user[2]
    discounts = await db.get_user_discounts(user_id)
    purchases = await db.get_user_purchases(user_id)
    ref_total = await db.count_referrals(user_id)
    ref_active = await db.count_referrals_active(user_id)
    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    text = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"💳 Баланс: <b>{balance:.0f} ₽</b>\n"
        f"🎁 Скидок {REFERRAL_DISCOUNT_PERCENT:.0f}%: <b>{discounts}</b>\n\n"
        f"📚 Купленные курсы:\n"
    )
    if purchases:
        for title, link in purchases:
            text += f"• {title}\n"
    else:
        text += "• Пока ничего не куплено\n"

    text += (
        f"\n👥 Рефералы: <b>{ref_total}</b> (купили курс: {ref_active})\n"
        f"🔗 Твоя реферальная ссылка:\n<code>{ref_link}</code>"
    )
    if DEBUG_MODE:
        text += "\n\n🧪 <i>Ты в режиме отладки</i>"

    photo_path = Path(IMAGES_DIR) / "profile.jpg"
    if photo_path.exists():
        try:
            msg = await callback.message.answer_photo(
                photo=FSInputFile(photo_path), caption=text,
                reply_markup=profile_keyboard(), parse_mode="HTML",
            )
            track(callback.from_user.id, msg.message_id)
            await callback.answer()
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить profile-фото: {e}")

    await send_tracked(callback, text, reply_markup=profile_keyboard())
    await callback.answer()


@router.callback_query(F.data == "my_ref_link")
async def show_ref_link(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()
    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{callback.from_user.id}"
    await send_tracked(
        callback,
        f"🔗 <b>Твоя реферальная ссылка:</b>\n\n<code>{ref_link}</code>\n\n"
        f"Отправь её друзьям! Когда они купят курс, ты получишь "
        f"<b>скидку {REFERRAL_DISCOUNT_PERCENT:.0f}%</b> на следующую покупку.",
        reply_markup=profile_keyboard(),
    )
    await callback.answer()


# --- Пополнение баланса -----------------------------------------------------
@router.callback_query(F.data == "menu_topup")
async def topup_menu(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    await state.clear()
    await state.set_state(TopUpState.waiting_for_amount)
    await send_tracked(
        callback,
        "💰 <b>Пополнение баланса</b>\n\n"
        "Введи сумму пополнения в рублях (от 50 до 50 000 ₽):",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()

@router.message(TopUpState.waiting_for_amount)
async def process_custom_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
    except (ValueError, AttributeError):
        await message.answer("Пожалуйста, введи число, например: 500")
        return

    # Проверка минимальной и максимальной суммы
    if amount < 50:
        await message.answer(
            "❌ <b>Минимальная сумма — 50 ₽.</b>\n"
            "Введи сумму от 50 до 50 000 ₽:",
            parse_mode="HTML",
        )
        return
    if amount > 50000:
        await message.answer(
            "❌ <b>Максимальная сумма — 50 000 ₽.</b>\n"
            "Введи сумму от 50 до 50 000 ₽:",
            parse_mode="HTML",
        )
        return

    await cleanup_by_message(message)
    await state.clear()

    if DEBUG_MODE or not (CRYPTO_PAY_ENABLED or MANUAL_PAYMENT_ENABLED):
        m = await message.answer(
            f"⚠️ Оплата временно недоступна.\n\nСумма: <b>{amount:.0f} ₽</b>",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        m = await message.answer(
            f"Выбери способ оплаты на <b>{amount:.0f} ₽</b>:",
            parse_mode="HTML",
            reply_markup=payment_keyboard(amount),
        )
    track(message.from_user.id, m.message_id)

async def get_course_invite_link(bot, course, user_id: int) -> str:
    """Возвращает ссылку на материалы курса (Яндекс/Google Диск)."""
    course_id, title, description, price, channel_link, cover, hidden = course
    return channel_link

@router.callback_query(F.data.startswith("pay_card_"))
async def process_card_payment(callback: CallbackQuery, state: FSMContext):
    # Если оплата реально не подключена — показываем заглушку
    if not PLATEGA_ENABLED:
        await callback.answer(
            "⚠️ Оплата картой временно недоступна. Мы уже подключаем этот способ!", 
            show_alert=True
        )
        return
        
    # Если PLATEGA_ENABLED=true (на будущее, когда получим API)
    # Здесь будет код создания ссылки через app.payments.create_payment_link
    await callback.answer("Перенаправляем на страницу оплаты...", show_alert=True)

@router.callback_query(F.data.startswith("pay_card_"))
async def process_card_payment(callback: CallbackQuery, state: FSMContext):
    # Сразу убираем "часики" загрузки
    await callback.answer()
    
    # ПРОВЕРКА: Если API ключей нет — показываем заглушку
    if not PAYMENTS_ENABLED:
        await callback.message.answer(
            "⚠️ <b>Оплата картой временно недоступна.</b>\n\n"
            "Мы уже подключаем этот способ. Пожалуйста, выберите другой способ оплаты или попробуйте позже.",
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard()
        )
        return

    # Если ключи есть — создаем платеж
    amount = float(callback.data.split("_")[2])
    user_id = callback.from_user.id

    order_id = generate_order_id(user_id)
    await db.create_pending_payment(order_id, user_id, amount)

    payment = await create_payment_link(amount, "Пополнение баланса", order_id)
    
    if not payment or not payment.get("redirect"):
        await callback.message.answer(
            "⚠️ Не удалось создать платёж. Пожалуйста, попробуйте позже или выберите другой способ.",
            reply_markup=back_to_menu_keyboard()
        )
        return

    await db.set_payment_transaction_id(order_id, payment.get("transaction_id"))
    
    # Отправляем ссылку на оплату
    link = html.escape(payment["redirect"])
    await callback.message.answer(
        f"💳 <b>Пополнение на {amount:.0f} ₽</b>\n\n"
        f"Перейдите по ссылке для оплаты:\n<a href='{link}'>Оплатить картой</a>",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard()
    )
    
# --- Обработчик отладочной оплаты (для режима DEBUG_MODE) -------------------
@router.callback_query(F.data.startswith("debug_pay_"))
async def debug_payment(callback: CallbackQuery, state: FSMContext):
    if not DEBUG_MODE:
        await callback.answer("Отладка отключена", show_alert=True)
        return

    await cleanup(callback)
    await state.clear()

    try:
        amount = float(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка суммы", show_alert=True)
        return

    await db.update_balance(callback.from_user.id, amount)
    await send_tracked(
        callback,
        f"🧪 <b>ТЕСТОВЫЙ ПЛАТЁЖ ПРОШЁЛ УСПЕШНО!</b>\n\n"
        f"Баланс пополнен на <b>{amount:.0f} ₽</b>.",
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer("Тестовый платёж успешен")