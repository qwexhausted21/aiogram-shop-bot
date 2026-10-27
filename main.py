"""
Точка входа. Запускает бота и (опционально) webhook-сервер.
"""
import asyncio
import logging
import sys

if sys.version_info >= (3, 15):
    print("⚠️  Ты запускаешь бота на Python 3.15, а библиотека aiogram его пока не поддерживает.")
    print("   Пожалуйста, используй Python 3.14:  py -3.14 main.py")
    sys.exit(1)

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from app.config import (
    BOT_TOKEN, DEBUG_MODE, ADMIN_IDS, WEBHOOK_URL, WEBHOOK_PORT
)
from app import database as db
from app import main_state
from app.webhook import start_webhook_server

from app.handlers.user import router as user_router
from app.handlers.admin import router as admin_router
from app.handlers.crypto import router as crypto_router, cp as crypto_cp
from app.handlers.manual import router as manual_router


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if DEBUG_MODE:
        logging.info("🧪 РЕЖИМ ОТЛАДКИ — реальные платежи отключены.")

    if not BOT_TOKEN:
        logging.error("В .env не указан BOT_TOKEN. Заполни .env и перезапусти.")
        return

    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    main_state.bot = bot

    await bot.set_my_commands(
        commands=[BotCommand(command="start", description="Главное меню")],
        scope=BotCommandScopeDefault(),
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                commands=[
                    BotCommand(command="start", description="Главное меню"),
                    BotCommand(command="admin", description="Админ-панель"),
                ],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as e:
            logging.warning(f"Не удалось установить команды для админа {admin_id}: {e}")

    if WEBHOOK_URL:
        try:
            await start_webhook_server(WEBHOOK_PORT)
        except Exception as e:
            logging.error(f"Не удалось запустить webhook-сервер: {e}")
    else:
        logging.info("Webhook не настроен (WEBHOOK_URL пуст).")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(crypto_router)
    dp.include_router(manual_router)

    logging.info("Бот запущен. Нажми Ctrl+C для остановки.")

    try:
        # Запускаем основного бота и поллинг CryptoPay параллельно
        tasks = [dp.start_polling(bot)]
        if crypto_cp:
            tasks.append(crypto_cp.start_polling())

        await asyncio.gather(*tasks)

    finally:
        if crypto_cp:
            await crypto_cp.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")