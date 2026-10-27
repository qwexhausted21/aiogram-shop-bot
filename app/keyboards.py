"""
Все клавиатуры бота — только инлайн-кнопки.
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import (
    DEBUG_MODE, SUPPORT_LINK,
    OFFER_LINK, TERMS_LINK, CRYPTO_PAY_ENABLED,
    MANUAL_PAYMENT_ENABLED, CHANNEL_LINK, PLATEGA_ENABLED
)

# --- Главное меню -----------------------------------------------------------
def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить курсы", callback_data="menu_buy")
    builder.button(text="👤 Личный кабинет", callback_data="menu_profile")
    builder.button(text="💰 Пополнить баланс", callback_data="menu_topup")

    if CHANNEL_LINK:
        builder.button(text="📢 Наш канал", url=CHANNEL_LINK)
    if SUPPORT_LINK:
        builder.button(text="🆘 Поддержка", url=SUPPORT_LINK)
    if OFFER_LINK:
        builder.button(text="📄 Политика конфиденциальности", url=OFFER_LINK)
    if TERMS_LINK:
        builder.button(text="📜 Пользовательское соглашение", url=TERMS_LINK)
        
    if is_admin:
        builder.button(text="⚙️ Админ-панель", callback_data="menu_admin")
        builder.adjust(1, 2, 2, 2, 1)
    else:
        builder.adjust(1, 2, 2, 1)
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    return builder.as_markup()


# --- Курсы ------------------------------------------------------------------
def courses_keyboard(courses) -> InlineKeyboardMarkup:
    """Кнопки со списком курсов + кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    for course in courses:
        course_id, title, description, price, channel_link, cover, hidden = course
        builder.button(
            text=f"{title} — {price:.0f} ₽",
            callback_data=f"course_{course_id}",
        )
    builder.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def course_details_keyboard(course_id: int, price: float) -> InlineKeyboardMarkup:
    """Кнопки под карточкой конкретного курса."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"✅ Купить за {price:.0f} ₽",
        callback_data=f"buy_{course_id}",
    )
    builder.button(text="⬅️ К списку курсов", callback_data="menu_buy")
    builder.adjust(1)
    return builder.as_markup()


def buy_confirm_keyboard(course_id: int, price: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"✅ Подтвердить покупку за {price:.0f} ₽",
        callback_data=f"confirm_buy_{course_id}",
    )
    builder.button(text="⬅️ К курсам", callback_data="menu_buy")
    builder.adjust(1)
    return builder.as_markup()


# --- Личный кабинет и баланс ------------------------------------------------
def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Моя реферальная ссылка", callback_data="my_ref_link")
    if SUPPORT_LINK:
        builder.button(text="🆘 Поддержка", url=SUPPORT_LINK)
    builder.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()


def payment_keyboard(amount: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопка Platega (Карта/СБП) — показываем ВСЕГДА
    builder.button(text="💳 Оплатить картой / СБП", callback_data=f"pay_card_{amount:.0f}")
        
    if CRYPTO_PAY_ENABLED:
        builder.button(text="🪙 Оплатить криптой", callback_data=f"pay_crypto_{amount:.0f}")
    if MANUAL_PAYMENT_ENABLED:
        builder.button(text="💸 Перевод по СБП (вручную)", callback_data=f"pay_manual_{amount:.0f}")
        
    builder.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

# --- Админ-панель -----------------------------------------------------------
def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить курс", callback_data="admin_add")
    builder.button(text="✏️ Изменить курс", callback_data="admin_edit")
    builder.button(text="🗑 Удалить курс", callback_data="admin_delete")
    builder.button(text="👁 Скрыть/показать курс", callback_data="admin_toggle")
    builder.button(text="📢 Рассылка о курсе", callback_data="admin_broadcast")
    builder.button(text="📰 Новость", callback_data="admin_news")
    builder.button(text="💸 Ручные платежи", callback_data="admin_manual_payments")  # <--- НОВАЯ КНОПКА
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="⬅️ В главное меню", callback_data="back_to_menu")
    builder.adjust(1, 2, 2, 2, 1)
    return builder.as_markup()


def admin_courses_keyboard(courses, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        course_id = course[0]
        title = course[1]
        hidden = course[6]
        mark = "🙈 " if hidden else ""
        builder.button(
            text=f"{mark}{title}",
            callback_data=f"admin_{action}_{course_id}",
        )
    builder.button(text="⬅️ В админ-панель", callback_data="menu_admin")
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_keyboard(course_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Да, удалить", callback_data=f"confirm_delete_{course_id}")
    builder.button(text="❌ Отмена", callback_data="admin_delete")
    builder.adjust(1)
    return builder.as_markup()


def edit_course_fields_keyboard(course_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_field_{course_id}_title")
    builder.button(text="Описание", callback_data=f"edit_field_{course_id}_description")
    builder.button(text="Цена", callback_data=f"edit_field_{course_id}_price")
    builder.button(text="Ссылка на материалы", callback_data=f"edit_field_{course_id}_channel_link") # <--- Текст изменен
    builder.button(text="Обложка", callback_data=f"edit_field_{course_id}_cover")
    builder.button(text="⬅️ К списку курсов", callback_data="admin_edit")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def broadcast_courses_keyboard(courses) -> InlineKeyboardMarkup:
    """Список курсов для выбора, о каком сделать рассылку."""
    builder = InlineKeyboardBuilder()
    for course in courses:
        course_id, title, description, price, channel_link, cover, hidden = course
        mark = "🙈 " if hidden else ""
        builder.button(
            text=f"{mark}{title}",
            callback_data=f"broadcast_{course_id}",
        )
    builder.button(text="⬅️ В админ-панель", callback_data="menu_admin")
    builder.adjust(1)
    return builder.as_markup()


def confirm_broadcast_keyboard(course_id: int) -> InlineKeyboardMarkup:
    """Подтверждение рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Да, разослать всем",
        callback_data=f"confirm_broadcast_{course_id}",
    )
    builder.button(text="❌ Отмена", callback_data="admin_broadcast")
    builder.adjust(1)
    return builder.as_markup()
def confirm_news_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение новостной рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Да, разослать всем", callback_data="confirm_news")
    builder.button(text="❌ Отмена", callback_data="menu_admin")
    builder.adjust(1)
    return builder.as_markup()