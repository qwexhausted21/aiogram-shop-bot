"""
Встроенный webhook-сервер для приёма уведомлений от Platega.
Запускается параллельно с ботом, если в .env указан WEBHOOK_URL.
"""
import logging

from aiohttp import web

from app import database as db


routes = web.RouteTableDef()


@routes.post("/platega/callback")
async def platega_callback(request: web.Request) -> web.Response:
    """Принимает уведомление от Platega о статусе платежа."""
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.post())

    logging.info(f"Platega callback получен: {data}")

    # Извлекаем ключевые поля (имена могут отличаться — сверить с docs.platega.io)
    transaction_id = data.get("id") or data.get("transactionId")
    order_id = data.get("orderId") or data.get("order_id")
    status = (data.get("status") or "").upper()

    logging.info(f"Platega callback: order={order_id}, tx={transaction_id}, status={status}")

    # Находим платёж в базе
    payment = None
    if order_id:
        payment = await db.get_pending_payment_by_order(order_id)
    if not payment and transaction_id:
        payment = await db.get_pending_payment_by_transaction(str(transaction_id))

    if not payment:
        logging.warning(f"Платёж не найден: order={order_id}, tx={transaction_id}")
        return web.json_response({"status": "not_found"}, status=404)

    p_order_id, user_id, amount, p_status = payment

    if p_status == "paid":
        logging.info(f"Платёж {p_order_id} уже был зачислен ранее — пропускаю.")
        return web.json_response({"status": "already_paid"})

    # Platega подтверждает оплату статусом CONFIRMED (сверить с docs)
    if status in ("CONFIRMED", "SUCCESS", "PAID", "SUCCEEDED"):
        await db.update_balance(user_id, amount)
        await db.mark_payment_paid(p_order_id)
        logging.info(f"✅ Платёж {p_order_id}: зачислено {amount} ₽ пользователю {user_id}")

        # Пытаемся уведомить пользователя
        try:
            from app.main_state import bot
            if bot:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ <b>Баланс пополнен!</b>\n\n"
                        f"Сумма: <b>{amount:.0f} ₽</b>\n"
                        f"Спасибо за оплату!"
                    ),
                    parse_mode="HTML",
                )
        except Exception as e:
            logging.warning(f"Не удалось уведомить пользователя {user_id}: {e}")

        return web.json_response({"status": "ok"})

    logging.info(f"Платёж {p_order_id}: статус {status} — не подтверждаем.")
    return web.json_response({"status": "accepted"})


async def start_webhook_server(port: int = 8080) -> None:
    """Запускает HTTP-сервер для приёма callback от Platega."""
    app = web.Application()
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Webhook-сервер запущен на порту {port}")