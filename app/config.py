"""
Загрузка всех настроек из файла .env.

Особенности этой версии:
- .env ищется строго рядом с этим файлом (config.py), а не в "текущей папке".
  Это спасает, когда бот запускают из PyCharm/IDE с другой рабочей директорией.
- override=True: значения из .env гарантированно перебивают всё, что могло
  остаться в переменных окружения от предыдущих запусков.
- Значения очищаются от пробелов и кавычек — устойчиво к опечаткам.
- В консоль печатается диагностика: какой файл прочитан и что в нём есть.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv


# --- Проверка версии Python ------------------------------------------------
# aiogram поддерживает Python до 3.14 включительно.
# Если заказчик случайно запустит на 3.15, бот не упадёт молча,
# а подскажет, что нужно использовать py -3.14.
if sys.version_info >= (3, 15):
    print("⚠️  Ты запускаешь бота на Python 3.15, а библиотека aiogram его пока не поддерживает.")
    print("   Пожалуйста, используй Python 3.14:  py -3.14 main.py")
    sys.exit(1)


# --- Загрузка .env ---------------------------------------------------------
# Путь к .env строго рядом с этим файлом (config.py).
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    # override=True — значения из .env перебивают уже существующие env-переменные
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    ENV_SOURCE = str(ENV_PATH)
else:
    # На всякий случай пробуем найти .env где-нибудь выше (напр. в родительской папке)
    fallback = find_dotenv(usecwd=True)
    if fallback:
        load_dotenv(dotenv_path=fallback, override=True)
        ENV_SOURCE = fallback
        print(f"⚠️  Файл .env не найден рядом с config.py, но найден здесь: {fallback}")
        print(f"   Рекомендую переместить .env в папку проекта: {BASE_DIR}")
    else:
        ENV_SOURCE = None
        print("=" * 64)
        print("❌ ФАЙЛ .env НЕ НАЙДЕН!")
        print(f"   Ожидался здесь: {ENV_PATH}")
        print("   Создай файл .env (скопируй .env.example) и заполни его.")
        print("=" * 64)


# --- Вспомогательные функции для чтения переменных -------------------------
def _get_str(key: str, default: str = "") -> str:
    """Возвращает строку без пробелов и обрамляющих кавычек."""
    value = os.getenv(key, default)
    if value is None:
        return default
    value = value.strip()
    # Убираем обрамляющие кавычки, если кто-то их поставил: "abc" или 'abc'
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    return value


def _get_bool(key: str, default: bool = False) -> bool:
    value = _get_str(key, str(default)).lower()
    return value in ("true", "1", "yes", "y", "on", "да")


def _get_float(key: str, default: float = 0.0) -> float:
    raw = _get_str(key, "")
    if not raw:
        return default
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        print(f"⚠️  Не удалось прочитать {key}={raw!r} как число, использую {default}")
        return default


def _get_admins(key: str) -> list[int]:
    raw = _get_str(key, "")
    result = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            print(f"⚠️  В {key} встретилось не число: {part!r}, пропускаю")
    return result


# --- Основные настройки -----------------------------------------------------
BOT_TOKEN: str = _get_str("BOT_TOKEN")
ADMIN_IDS: list[int] = _get_admins("ADMIN_IDS")
DEBUG_MODE: bool = _get_bool("DEBUG_MODE", default=True)

SUPPORT_LINK: str = _get_str("SUPPORT_LINK", "https://t.me/telegram")
OFFER_LINK: str = _get_str("OFFER_LINK", "https://example.com/oferta")
TERMS_LINK: str = _get_str("TERMS_LINK", "https://example.com/terms")
CHANNEL_LINK: str = _get_str("CHANNEL_LINK")

STARS_ENABLED: bool = _get_bool("STARS_ENABLED", default=False)

CRYPTO_PAY_TOKEN: str = _get_str("CRYPTO_PAY_TOKEN")
CRYPTO_PAY_ENABLED: bool = _get_bool("CRYPTO_PAY_ENABLED", default=False)

MANUAL_PAYMENT_PHONE: str = _get_str("MANUAL_PAYMENT_PHONE")
MANUAL_PAYMENT_ENABLED: bool = _get_bool("MANUAL_PAYMENT_ENABLED", default=False)

REFERRAL_DISCOUNT_PERCENT: float = _get_float("REFERRAL_DISCOUNT_PERCENT", default=30.0)

# --- Platega (нужны только в боевом режиме) --------------------------------
PLATEGA_MERCHANT_ID: str = _get_str("PLATEGA_MERCHANT_ID")
PLATEGA_SECRET: str = _get_str("PLATEGA_SECRET")
# Платежи считаются подключёнными, только если заданы оба ключа Platega
PAYMENTS_ENABLED: bool = bool(PLATEGA_MERCHANT_ID and PLATEGA_SECRET)

# --- Способы оплаты ---
PLATEGA_ENABLED: bool = _get_bool("PLATEGA_ENABLED", default=False)
CRYPTO_PAY_ENABLED: bool = _get_bool("CRYPTO_PAY_ENABLED", default=False)
MANUAL_PAYMENT_ENABLED: bool = _get_bool("MANUAL_PAYMENT_ENABLED", default=False)
CRYPTO_PAY_TOKEN: str = _get_str("CRYPTO_PAY_TOKEN")
MANUAL_PAYMENT_PHONE: str = _get_str("MANUAL_PAYMENT_PHONE")

# --- Служебные пути --------------------------------------------------------
DB_PATH: str = str(BASE_DIR / "bot.db")
IMAGES_DIR: str = str(BASE_DIR / "images")

# Webhook (нужен для реальных платежей)
WEBHOOK_URL: str = _get_str("WEBHOOK_URL")
WEBHOOK_PORT: int = int(_get_str("WEBHOOK_PORT", "8080"))

# --- Диагностика при старте ------------------------------------------------
print("=" * 64)
print("📄 Конфигурация загружена")
print(f"   Файл .env:      {ENV_SOURCE or '❌ НЕ НАЙДЕН'}")
print(f"   BOT_TOKEN:      {'✅ задан' if BOT_TOKEN else '❌ ПУСТОЙ'}")
print(f"   ADMIN_IDS:      {ADMIN_IDS if ADMIN_IDS else '❌ пусто'}")
print(f"   DEBUG_MODE:     {DEBUG_MODE}")
print(f"   SUPPORT_LINK:   {SUPPORT_LINK}")
print(f"   OFFER_LINK:     {OFFER_LINK}")
print(f"   TERMS_LINK:     {TERMS_LINK}")
print(f"   CHANNEL_LINK:   {CHANNEL_LINK or '— не задана'}")
print(f"   Скидка реферала:{REFERRAL_DISCOUNT_PERCENT}%")
print(f"   PLATEGA_ID:     {'✅ задан' if PLATEGA_MERCHANT_ID else '— пусто (норм для отладки)'}")
print(f"   PLATEGA_SECRET: {'✅ задан' if PLATEGA_SECRET else '— пусто (норм для отладки)'}")
print("=" * 64)
print(f"   WEBHOOK_URL:    {WEBHOOK_URL or '— пусто (платежи не заработают)'}")
print(f"   WEBHOOK_PORT:   {WEBHOOK_PORT}")
print(f"   PLATEGA_ENABLED:{PLATEGA_ENABLED}")

