"""
Простой трекер сообщений бота для каждого пользователя.
Нужен, чтобы при переходе в новое меню удалять предыдущие сообщения.
Хранит ID сообщений в памяти (при перезапуске бота — сбрасывается).
"""

# Словарь: user_id -> список ID сообщений
_messages: dict[int, list[int]] = {}


def track(user_id: int, message_id: int) -> None:
    """Запомнить ID сообщения, чтобы потом его можно было удалить."""
    _messages.setdefault(user_id, []).append(message_id)


async def cleanup(callback, bot=None) -> None:
    """
    Удаляет все ранее отправленные сообщения бота этому пользователю
    + само сообщение с нажатой кнопкой.
    """
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    _bot = bot or callback.bot

    for msg_id in _messages.get(user_id, []):
        try:
            await _bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    _messages[user_id] = []

    # На всякий случай удаляем и текущее сообщение с кнопкой,
    # если его не было в трекере.
    try:
        await callback.message.delete()
    except Exception:
        pass


async def cleanup_by_message(message, bot=None) -> None:
    """То же самое, но для обычных Message-хендлеров (например /start)."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    _bot = bot or message.bot

    for msg_id in _messages.get(user_id, []):
        try:
            await _bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    _messages[user_id] = []