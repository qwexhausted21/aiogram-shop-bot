"""
Работа с платежами через Platega.
Готово к использованию: как только в .env появятся ключи, DEBUG_MODE=false
и WEBHOOK_URL — реальные платежи заработают.
"""
import logging
import uuid

import aiohttp

from app.config import (
    DEBUG_MODE,
    PAYMENTS_ENABLED,
    PLATEGA_MERCHANT_ID,
    PLATEGA_SECRET,
    WEBHOOK_URL,
)


# Базовый URL и эндпоинт Platega.
# ⚠️ Если в docs.platega.io указан другой путь — поменяй здесь.
PLATEGA_BASE_URL = "https://app.platega.io"
PLATEGA_CREATE_ENDPOINT = "/transaction/process"


def generate_order_id(user_id: int) -> str:
    """Генерирует уникальный ID платежа для передачи в Platega."""
    return f"topup_{user_id}_{uuid.uuid4().hex[:10]}"


async def create_payment_link(amount: float, description: str, order_id: str) -> dict | None:
    """
    Создаёт платёж в Platega.
    Возвращает словарь {'redirect': url, 'transaction_id': id} или None при ошибке.
    """
    if not PAYMENTS_ENABLED:
        logging.info("Платежи не подключены: нет ключей Platega.")
        return None

    if DEBUG_MODE:
        logging.info("🧪 РЕЖИМ ОТЛАДКИ — реальный Platega не вызывается.")
        return None

    if not WEBHOOK_URL:
        logging.warning(
            "WEBHOOK_URL пуст — не сможем получить подтверждение оплаты. "
            "Укажи его в .env, когда будет готов сервер."
        )
        return None

    payload = {
        "amount": round(amount, 2),
        "currency": "RUB",
        "description": description,
        "orderId": order_id,
        "callbackUrl": WEBHOOK_URL,
    }
    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = PLATEGA_BASE_URL + PLATEGA_CREATE_ENDPOINT
    logging.info(f"Platega: отправляю запрос на {url}, order_id={order_id}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=15,
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logging.error(f"Platega: HTTP {resp.status} — {text}")
                    return None

                try:
                    data = await resp.json()
                except Exception:
                    logging.error(f"Platega: невалидный JSON — {text}")
                    return None

                logging.info(f"Platega: успешный ответ — {data}")
                redirect = (
                    data.get("redirect")
                    or data.get("paymentUrl")
                    or data.get("payUrl")
                )
                transaction_id = (
                    data.get("id")
                    or data.get("transactionId")
                    or data.get("transaction_id")
                )
                if not redirect:
                    logging.error(f"Platega: нет redirect в ответе — {data}")
                    return None

                return {"redirect": redirect, "transaction_id": transaction_id}

    except Exception as e:
        logging.error(f"Platega: ошибка при создании платежа — {e}")
        return None