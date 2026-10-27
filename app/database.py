"""
Работа с базой данных SQLite через aiosqlite.
"""
import aiosqlite
from app.config import DB_PATH


async def init_db() -> None:
    """Создаёт все таблицы, если их ещё нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_payments (
                order_id       TEXT PRIMARY KEY,
                user_id        INTEGER NOT NULL,
                amount         REAL NOT NULL,
                transaction_id TEXT,
                status         TEXT DEFAULT 'pending',
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS manual_payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_messages (
                user_id     INTEGER NOT NULL,
                order_id    TEXT NOT NULL,
                message_id  INTEGER NOT NULL,
                PRIMARY KEY (user_id, order_id)
            )
        """)

        # Миграция для старых баз: добавляем новые поля, если их нет
        cursor = await db.execute("PRAGMA table_info(users)")
        existing_cols = [row[1] for row in await cursor.fetchall()]
        if "discounts" not in existing_cols:
            await db.execute("ALTER TABLE users ADD COLUMN discounts INTEGER DEFAULT 0")
        if "ref_counted" not in existing_cols:
            await db.execute("ALTER TABLE users ADD COLUMN ref_counted INTEGER DEFAULT 0")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                description  TEXT,
                price        REAL NOT NULL,
                channel_link TEXT,
                cover_file_id TEXT,
                is_hidden    INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                course_id   INTEGER NOT NULL,
                amount      REAL NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            )
        """)

        await db.commit()


# --- Пользователи -----------------------------------------------------------

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, balance, referrer_id, discounts, ref_counted "
            "FROM users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            return await cur.fetchone()


async def create_user(user_id: int, username: str, referrer_id: int | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)",
            (user_id, username, referrer_id),
        )
        await db.commit()


async def update_balance(user_id: int, amount: float) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0


# --- Скидки и рефералы ------------------------------------------------------

async def get_user_discounts(user_id: int) -> int:
    """Сколько скидок 30% накопилось у пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT discounts FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def add_discount(user_id: int) -> None:
    """Начисляет +1 скидку 30%."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET discounts = discounts + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def use_discount(user_id: int) -> bool:
    """Списывает 1 скидку. True — если получилось (была хотя бы 1)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT discounts FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row or row[0] <= 0:
                return False
        await db.execute("UPDATE users SET discounts = discounts - 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return True


async def is_ref_counted(user_id: int) -> bool:
    """Засчитан ли этот пользователь как реферал (купил курс)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ref_counted FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else False


async def mark_ref_counted(user_id: int) -> None:
    """Помечает пользователя как «засчитанного реферала»."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET ref_counted = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def count_referrals(referrer_id: int) -> int:
    """Сколько всего пользователей пришли по этой реферальной ссылке."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ?", (referrer_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_referrals_active(referrer_id: int) -> int:
    """Сколько рефералов купили курс (засчитаны)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ? AND ref_counted = 1",
            (referrer_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_all_user_ids() -> list[int]:
    """Все ID пользователей бота (для рассылок)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]


# --- Курсы ------------------------------------------------------------------

async def get_visible_courses():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM courses WHERE is_hidden = 0") as cur:
            return await cur.fetchall()


async def get_all_courses():
    """Все курсы, включая скрытые (для админки)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM courses") as cur:
            return await cur.fetchall()


async def get_course(course_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)) as cur:
            return await cur.fetchone()


async def add_course(title: str, description: str, price: float,
                     channel_link: str, cover_file_id: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO courses (title, description, price, channel_link, cover_file_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, description, price, channel_link, cover_file_id),
        )
        await db.commit()
        return cur.lastrowid


async def update_course(course_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [course_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE courses SET {sets} WHERE id = ?", values)
        await db.commit()


async def delete_course(course_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        await db.commit()


async def toggle_course_visibility(course_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE courses SET is_hidden = 1 - is_hidden WHERE id = ?", (course_id,)
        )
        await db.commit()


# --- Покупки ----------------------------------------------------------------

async def add_purchase(user_id: int, course_id: int, amount: float) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO purchases (user_id, course_id, amount) VALUES (?, ?, ?)",
            (user_id, course_id, amount),
        )
        await db.commit()


async def get_user_purchases(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT c.title, c.channel_link
               FROM purchases p
               JOIN courses c ON c.id = p.course_id
               WHERE p.user_id = ?""",
            (user_id,),
        ) as cur:
            return await cur.fetchall()


# --- Статистика -------------------------------------------------------------

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM purchases") as cur:
            purchases = (await cur.fetchone())[0]

        async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM purchases") as cur:
            money = (await cur.fetchone())[0]

        return {"users": users, "purchases": purchases, "money": money}
    # --- Ожидающие платежи (для Platega) ---------------------------------------

async def create_pending_payment(order_id: str, user_id: int, amount: float) -> None:
    """Создаёт запись о новом платеже со статусом pending."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO pending_payments (order_id, user_id, amount) VALUES (?, ?, ?)",
            (order_id, user_id, amount),
        )
        await db.commit()


async def set_payment_transaction_id(order_id: str, transaction_id: str | None) -> None:
    """Сохраняет ID транзакции из ответа Platega."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET transaction_id = ? WHERE order_id = ?",
            (transaction_id, order_id),
        )
        await db.commit()


async def get_pending_payment_by_order(order_id: str):
    """Возвращает запись платежа по нашему order_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT order_id, user_id, amount, status FROM pending_payments WHERE order_id = ?",
            (order_id,),
        ) as cur:
            return await cur.fetchone()


async def get_pending_payment_by_transaction(transaction_id: str):
    """Возвращает запись платежа по ID транзакции Platega."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT order_id, user_id, amount, status FROM pending_payments WHERE transaction_id = ?",
            (transaction_id,),
        ) as cur:
            return await cur.fetchone()


async def mark_payment_paid(order_id: str) -> None:
    """Помечает платёж как оплаченный."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET status = 'paid' WHERE order_id = ?",
            (order_id,),
        )
        await db.commit()

        # --- Ручные платежи ---------------------------------------------------------

async def create_manual_payment(user_id: int, amount: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO manual_payments (user_id, amount) VALUES (?, ?)",
            (user_id, amount),
        )
        await db.commit()
        return cur.lastrowid

async def get_pending_manual_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, user_id, amount, created_at FROM manual_payments WHERE status = 'pending'"
        ) as cur:
            return await cur.fetchall()

async def confirm_manual_payment(payment_id: int) -> tuple[int, float] | None:
    """Подтверждает платёж и возвращает (user_id, amount) для начисления."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, amount FROM manual_payments WHERE id = ? AND status = 'pending'",
            (payment_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
        
        await db.execute(
            "UPDATE manual_payments SET status = 'paid' WHERE id = ?",
            (payment_id,),
        )
        await db.commit()
        return row

async def save_payment_message(user_id: int, order_id: str, message_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_messages (user_id, order_id, message_id) VALUES (?, ?, ?)",
            (user_id, order_id, message_id),
        )
        await db.commit()

async def get_payment_message(user_id: int, order_id: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id FROM user_messages WHERE user_id = ? AND order_id = ?",
            (user_id, order_id),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def get_manual_payment_by_id(payment_id: int):
    """Возвращает данные конкретной заявки на ручной перевод."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, user_id, amount, status FROM manual_payments WHERE id = ?",
            (payment_id,),
        ) as cur:
            return await cur.fetchone()