"""
Админ-панель.
"""
import logging
import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import database as db
from app.config import ADMIN_IDS
from app.keyboards import (
    admin_menu, admin_courses_keyboard, confirm_delete_keyboard,
    edit_course_fields_keyboard, broadcast_courses_keyboard,
    confirm_broadcast_keyboard, confirm_news_keyboard
)
from app.tracker import track, cleanup, cleanup_by_message

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class CourseForm(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_channel_link = State()
    waiting_cover = State()


class EditFieldForm(StatesGroup):
    waiting_value = State()


class NewsForm(StatesGroup):
    waiting_text = State()
    waiting_confirm = State()


async def send_tracked(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    msg = await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    track(callback.from_user.id, msg.message_id)
    return msg


async def send_tracked_msg(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    m = await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    track(message.from_user.id, m.message_id)
    return m


HINT_LINK = (
    "Введи <b>ссылку на материалы</b> (Яндекс.Диск, Google Drive и т.д.):\n\n"
    "✅ <code>https://disk.yandex.ru/d/...</code>\n"
    "✅ <code>https://drive.google.com/...</code>\n\n"
    "⚠️ Убедись, что доступ по ссылке открыт!"
)


# --- Команда /admin ---------------------------------------------------------
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет доступа к админ-панели.")
        return
    await cleanup_by_message(message)
    await state.clear()
    await send_tracked_msg(
        message,
        "⚙️ <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_menu(),
    )


# --- Вход в админ-панель ----------------------------------------------------
@router.callback_query(F.data == "menu_admin")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await cleanup(callback)
    await state.clear()
    await send_tracked(
        callback, "⚙️ <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_menu(),
    )
    await callback.answer()


# --- Добавить курс ----------------------------------------------------------
@router.callback_query(F.data == "admin_add")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await cleanup(callback)
    await state.clear()
    await state.set_state(CourseForm.waiting_title)
    await send_tracked(
        callback,
        "➕ <b>Добавление курса</b>\n\n"
        "Шаг 1 из 5. Введи <b>название</b> курса:",
        reply_markup=None,
    )
    await callback.answer()


@router.message(CourseForm.waiting_title)
async def add_course_title(message: Message, state: FSMContext):
    await cleanup_by_message(message)
    await state.update_data(title=message.text)
    await state.set_state(CourseForm.waiting_description)
    await send_tracked_msg(message, "Шаг 2 из 5. Введи <b>описание</b> курса:")


@router.message(CourseForm.waiting_description)
async def add_course_description(message: Message, state: FSMContext):
    await cleanup_by_message(message)
    await state.update_data(description=message.text)
    await state.set_state(CourseForm.waiting_price)
    await send_tracked_msg(message, "Шаг 3 из 5. Введи <b>цену</b> в рублях (только число):")


@router.message(CourseForm.waiting_price)
async def add_course_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").strip())
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введи положительное число, например: 990")
        return
    await cleanup_by_message(message)
    await state.update_data(price=price)
    await state.set_state(CourseForm.waiting_channel_link)
    await send_tracked_msg(message, "Шаг 4 из 5. " + HINT_LINK)


@router.message(CourseForm.waiting_channel_link)
async def add_course_channel(message: Message, state: FSMContext):
    if not message.text or not message.text.startswith("http"):
        await message.answer(
            "⚠️ Пожалуйста, отправь корректную ссылку, начинающуюся с http:// или https://\n\n" + HINT_LINK,
            parse_mode="HTML",
        )
        return

    await cleanup_by_message(message)
    await state.update_data(channel_link=message.text.strip())
    await state.set_state(CourseForm.waiting_cover)
    await send_tracked_msg(
        message,
        f"✅ Ссылка сохранена.\n\n"
        "Шаг 5 из 5. Отправь <b>обложку</b> курса как фото.\n"
        "Или введи «-», чтобы добавить без обложки.",
    )


@router.message(CourseForm.waiting_cover)
async def add_course_cover(message: Message, state: FSMContext):
    cover_file_id = None
    if message.text and message.text.strip() == "-":
        cover_file_id = None
    elif message.photo:
        cover_file_id = message.photo[-1].file_id
    else:
        await message.answer("Отправь фото или введи «-» для пропуска.")
        return

    await cleanup_by_message(message)
    data = await state.get_data()
    await db.add_course(
        title=data["title"],
        description=data["description"],
        price=data["price"],
        channel_link=data["channel_link"],
        cover_file_id=cover_file_id,
    )
    await state.clear()
    await send_tracked_msg(
        message,
        f"✅ Курс «{data['title']}» добавлен!\n\n⚙️ Админ-панель:",
        reply_markup=admin_menu(),
    )


# --- Изменить курс ----------------------------------------------------------
@router.callback_query(F.data == "admin_edit")
async def edit_course_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await cleanup(callback)
    await state.clear()
    courses = await db.get_all_courses()
    if not courses:
        await send_tracked(callback, "Нет курсов для редактирования.", reply_markup=admin_menu())
        await callback.answer()
        return
    await send_tracked(
        callback, "✏️ Выбери курс для редактирования:",
        reply_markup=admin_courses_keyboard(courses, action="edit"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_"))
async def edit_course_choose(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[2])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    _, title, description, price, channel_link, cover, hidden = course
    text = (
        f"✏️ <b>Редактирование курса</b>\n\n"
        f"Название: {title}\n"
        f"Цена: {price:.0f} ₽\n"
        f"Ссылка: <code>{channel_link}</code>\n\n"
        f"Что изменить?"
    )
    await send_tracked(callback, text, reply_markup=edit_course_fields_keyboard(course_id))
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field_"))
async def edit_field_start(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    parts = callback.data.split("_")
    course_id = int(parts[2])
    # Берем всё, что идет после ID курса, и склеиваем обратно
    field = "_".join(parts[3:]) 

    await state.update_data(edit_course_id=course_id, edit_field=field)
    await state.set_state(EditFieldForm.waiting_value)

    prompts = {
        "title": "Введи новое название курса:",
        "description": "Введи новое описание курса:",
        "price": "Введи новую цену (только число):",
        "channel_link": HINT_LINK,  # Теперь сюда точно придет "channel_link"
        "cover": "Отправь новую обложку как фото (или введи «-» для удаления):",
    }
    await send_tracked(callback, prompts.get(field, "Введи новое значение:"), reply_markup=None)
    await callback.answer()
    
@router.message(EditFieldForm.waiting_value)
async def edit_field_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    field = data["edit_field"]

    if field == "price":
        try:
            value = float(message.text.replace(",", ".").strip())
            if value <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            await message.answer("Введи положительное число, например: 990")
            return
    elif field == "channel_link":
        if not message.text or not message.text.startswith("http"):
            await message.answer("⚠️ Пожалуйста, отправь ссылку, начинающуюся с http:// или https://\n\n" + HINT_LINK, parse_mode="HTML")
            return
        value = message.text.strip()
    elif field == "cover":
        if message.text and message.text.strip() == "-":
            value = None
        elif message.photo:
            value = message.photo[-1].file_id
        else:
            await message.answer("Отправь фото или введи «-» для удаления обложки.")
            return
    else:
        value = message.text

    await cleanup_by_message(message)
    if field == "cover":
        await db.update_course(course_id, cover_file_id=value)
    else:
        await db.update_course(course_id, **{field: value})

    await state.clear()

    course = await db.get_course(course_id)
    _, title, description, price, channel_link, cover, hidden = course
    await send_tracked_msg(
        message,
        f"✅ Поле обновлено.\n\n"
        f"Название: {title}\n"
        f"Цена: {price:.0f} ₽\n"
        f"Ссылка: <code>{channel_link}</code>\n\n"
        f"Что изменить ещё?",
        reply_markup=edit_course_fields_keyboard(course_id),
    )


# --- Удалить курс -----------------------------------------------------------
@router.callback_query(F.data == "admin_delete")
async def delete_course_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await cleanup(callback)
    await state.clear()
    courses = await db.get_all_courses()
    if not courses:
        await send_tracked(callback, "Нет курсов для удаления.", reply_markup=admin_menu())
        await callback.answer()
        return
    await send_tracked(
        callback, "🗑 Выбери курс для удаления:",
        reply_markup=admin_courses_keyboard(courses, action="delete"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_"))
async def delete_course_confirm(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[2])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return
    title = course[1]
    await send_tracked(
        callback,
        f"Ты уверен, что хочешь удалить курс <b>«{title}»</b>?\nЭто действие нельзя отменить.",
        reply_markup=confirm_delete_keyboard(course_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_course_final(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[2])
    await db.delete_course(course_id)
    await send_tracked(callback, "🗑 Курс удалён.\n\n⚙️ Админ-панель:", reply_markup=admin_menu())
    await callback.answer("Удалено")


# --- Скрыть/показать курс ---------------------------------------------------
@router.callback_query(F.data == "admin_toggle")
async def toggle_course_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await cleanup(callback)
    await state.clear()
    courses = await db.get_all_courses()
    if not courses:
        await send_tracked(callback, "Нет курсов.", reply_markup=admin_menu())
        await callback.answer()
        return
    await send_tracked(
        callback, "👁 Выбери курс, чтобы скрыть или показать его:",
        reply_markup=admin_courses_keyboard(courses, action="toggle"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_toggle_"))
async def toggle_course(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[2])
    await db.toggle_course_visibility(course_id)
    courses = await db.get_all_courses()
    await send_tracked(
        callback, "✅ Готово. Выбери курс, чтобы скрыть или показать его:",
        reply_markup=admin_courses_keyboard(courses, action="toggle"),
    )
    await callback.answer("Готово")


# --- Рассылка о курсе -------------------------------------------------------
@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await cleanup(callback)
    await state.clear()

    courses = await db.get_all_courses()
    if not courses:
        await send_tracked(
            callback,
            "Нет курсов, о которых можно сделать рассылку.",
            reply_markup=admin_menu(),
        )
        await callback.answer()
        return

    await send_tracked(
        callback,
        "📢 <b>Рассылка</b>\n\nВыбери курс, о котором хочешь оповестить всех пользователей:",
        reply_markup=broadcast_courses_keyboard(courses),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_"))
async def broadcast_preview(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[1])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    _, title, description, price, channel_link, cover, hidden = course

    text = (
        f"📢 <b>Предпросмотр рассылки</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{description}\n\n"
        f"💰 Цена: <b>{price:.0f} ₽</b>\n\n"
        f"<i>Сообщение будет отправлено всем пользователям бота.</i>\n\n"
        f"Разослать?"
    )
    await send_tracked(
        callback, text,
        reply_markup=confirm_broadcast_keyboard(course_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_broadcast_"))
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    await cleanup(callback)
    course_id = int(callback.data.split("_")[2])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    _, title, description, price, channel_link, cover, hidden = course

    await send_tracked(
        callback,
        f"🚀 Рассылка курса «{title}» запущена...\n"
        f"Это может занять некоторое время.",
        reply_markup=None,
    )
    await callback.answer("Рассылка запущена")

    asyncio.create_task(_do_broadcast(callback.bot, course, callback.from_user.id))


async def _do_broadcast(bot, course, admin_chat_id: int):
    course_id, title, description, price, channel_link, cover, hidden = course

    text = (
        f"🎉 <b>Новый курс!</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{description}\n\n"
        f"💰 Цена: <b>{price:.0f} ₽</b>\n\n"
        f"Нажми «🛒 Купить курсы», чтобы узнать подробности и купить."
    )

    user_ids = await db.get_all_user_ids()
    logging.info(f"Рассылка курса {course_id}: {len(user_ids)} получателей")

    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            if cover:
                await bot.send_photo(
                    chat_id=user_id, photo=cover,
                    caption=text, parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=user_id, text=text, parse_mode="HTML",
                )
            success += 1
        except Exception as e:
            failed += 1
            logging.warning(f"Рассылка: не удалось отправить пользователю {user_id}: {e}")

        await asyncio.sleep(0.05)

    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"✅ <b>Рассылка завершена</b>\n\n"
                f"Курс: {title}\n"
                f"Отправлено: <b>{success}</b>\n"
                f"Не доставлено: <b>{failed}</b>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить отчёт о рассылке: {e}")


# --- Новостная рассылка -----------------------------------------------------
@router.callback_query(F.data == "admin_news")
async def news_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await cleanup(callback)
    await state.clear()
    await state.set_state(NewsForm.waiting_text)

    await send_tracked(
        callback,
        "📰 <b>Новостная рассылка</b>\n\n"
        "Отправь сообщение, которое уйдёт всем пользователям бота.\n\n"
        "• Можно просто текст.\n"
        "• Можно фото с подписью.\n"
        "• Поддерживается HTML-разметка: <b>жирный</b>, <i>курсив</i>, "
        "<code>код</code>, <a href='https://example.com'>ссылки</a>.\n\n"
        "Отправь сообщение:",
        reply_markup=None,
    )
    await callback.answer()


@router.message(NewsForm.waiting_text)
async def news_get_text(message: Message, state: FSMContext):
    text = message.html_text if message.text else (message.caption or "")
    photo_id = message.photo[-1].file_id if message.photo else None

    if not text and not photo_id:
        await message.answer("Нужно отправить текст или фото с подписью.")
        return

    await state.update_data(news_text=text, news_photo=photo_id)
    await state.set_state(NewsForm.waiting_confirm)

    preview_text = f"👀 <b>Предпросмотр</b>\n\n{text}" if text else "👀 <b>Предпросмотр</b>"

    if photo_id:
        await message.answer_photo(
            photo=photo_id, caption=preview_text,
            parse_mode="HTML", reply_markup=confirm_news_keyboard(),
        )
    else:
        await message.answer(
            preview_text, parse_mode="HTML",
            reply_markup=confirm_news_keyboard(),
        )


@router.callback_query(F.data == "confirm_news")
async def news_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    text = data.get("news_text", "")
    photo_id = data.get("news_photo")

    await cleanup(callback)
    await state.clear()

    await send_tracked(
        callback,
        "🚀 Новостная рассылка запущена...\nЭто может занять некоторое время.",
        reply_markup=None,
    )
    await callback.answer("Рассылка запущена")

    asyncio.create_task(
        _do_news_broadcast(callback.bot, text, photo_id, callback.from_user.id)
    )


async def _do_news_broadcast(bot, text: str, photo_id: str | None, admin_chat_id: int):
    user_ids = await db.get_all_user_ids()
    logging.info(f"Новостная рассылка: {len(user_ids)} получателей")

    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            if photo_id:
                await bot.send_photo(
                    chat_id=user_id, photo=photo_id,
                    caption=text or None, parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=user_id, text=text, parse_mode="HTML",
                )
            success += 1
        except Exception as e:
            failed += 1
            logging.warning(f"Новость: не удалось отправить {user_id}: {e}")

        await asyncio.sleep(0.05)

    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=(
                f"✅ <b>Новостная рассылка завершена</b>\n\n"
                f"Отправлено: <b>{success}</b>\n"
                f"Не доставлено: <b>{failed}</b>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить отчёт о новости: {e}")


# --- Статистика -------------------------------------------------------------
@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await cleanup(callback)
    await state.clear()
    stats = await db.get_stats()
    await send_tracked(
        callback,
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{stats['users']}</b>\n"
        f"🛒 Покупок: <b>{stats['purchases']}</b>\n"
        f"💰 Денег пришло: <b>{stats['money']:.0f} ₽</b>",
        reply_markup=admin_menu(),
    )
    await callback.answer()


# --- Ручные платежи ---------------------------------------------------------
@router.callback_query(F.data == "admin_manual_payments")
async def show_manual_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await cleanup(callback)
    
    payments = await db.get_pending_manual_payments()
    if not payments:
        await send_tracked(callback, "Нет ожидающих ручных платежей.", reply_markup=admin_menu())
        await callback.answer()
        return
    
    text = "💸 <b>Ожидающие ручные платежи:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for p in payments:
        p_id, u_id, amount, date = p
        text += f"ID: {p_id} | User: {u_id} | {amount} ₽ | {date}\n"
        builder.button(text=f"✅ Подтвердить #{p_id}", callback_data=f"admin_confirm_manual_{p_id}")
    
    builder.button(text="⬅️ В админ-панель", callback_data="menu_admin")
    builder.adjust(1)
    
    await send_tracked(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_manual_"))
async def confirm_manual_payment_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await cleanup(callback)
    p_id = int(callback.data.split("_")[3])
    result = await db.confirm_manual_payment(p_id)
    
    if result:
        user_id, amount = result
        await db.update_balance(user_id, amount)
        
        try:
            from app.main_state import bot
            if bot:
                await bot.send_message(
                    user_id, 
                    f"✅ Ваш платёж на сумму <b>{amount:.0f} ₽</b> подтверждён! Баланс пополнен.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
            
        await send_tracked(
            callback, 
            f"✅ Платёж #{p_id} подтверждён. Пользователю {user_id} зачислено {amount} ₽.",
            reply_markup=admin_menu()
        )
    else:
        await send_tracked(
            callback, 
            f"❌ Платёж #{p_id} не найден или уже подтверждён.",
            reply_markup=admin_menu()
        )
    await callback.answer()