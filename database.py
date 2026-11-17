import aiosqlite
from typing import Optional, List, Dict, Any
from config import DB_PATH, SUPPORT_CHAT_ID as CONFIG_SUPPORT_CHAT_ID

DEFAULT_DEPARTMENTS = [
    {"code": "it", "name": "💻 IT-відділ"},
    {"code": "buh", "name": "📊 Бухгалтерія"},
    {"code": "sklad", "name": "📦 Склад"},
    {"code": "office", "name": "🏢 Офіс"}
]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                user_id INTEGER UNIQUE NULL,
                username TEXT NULL,
                first_name TEXT NULL,
                selected_dept TEXT NULL,
                registered_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_message_id INTEGER NOT NULL,
                shop_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_msg ON messages_map (group_message_id)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_user_id INTEGER NOT NULL,
                shop_name TEXT NOT NULL,
                dept_code TEXT NULL,
                dept_name TEXT NULL,
                group_message_id INTEGER NOT NULL,
                shop_message_id INTEGER NULL,
                status TEXT DEFAULT 'open',
                is_urgent INTEGER DEFAULT 0,
                worker_name TEXT NULL,
                rating INTEGER NULL,
                message_text TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP NULL
            )
        """)

        # Безпечна авто-міграція для існуючих таблиць
        for migration in [
            "ALTER TABLE shops ADD COLUMN selected_dept TEXT NULL",
            "ALTER TABLE tickets ADD COLUMN dept_code TEXT NULL",
            "ALTER TABLE tickets ADD COLUMN dept_name TEXT NULL"
        ]:
            try:
                await db.execute(migration)
            except Exception:
                pass

        await db.commit()

# ----------------- Відділи компанії -----------------

async def set_department(code: str, name: str, chat_id: int):
    code = code.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO departments (code, name, chat_id)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET name = excluded.name, chat_id = excluded.chat_id, updated_at = CURRENT_TIMESTAMP
        """, (code, name.strip(), chat_id))
        await db.commit()

async def get_department(code: str) -> Optional[Dict[str, Any]]:
    code = code.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM departments WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_departments() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM departments ORDER BY code ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_department_by_chat_id(chat_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM departments WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def set_shop_selected_dept(user_id: int, dept_code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE shops SET selected_dept = ? WHERE user_id = ?", (dept_code, user_id))
        await db.commit()

# ----------------- Підтримка зворотної сумісності (get_support_chat_id) -----------------

async def set_support_chat_id(chat_id: int):
    await set_department("it", "💻 IT-відділ", chat_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value) VALUES ('support_chat_id', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (str(chat_id),))
        await db.commit()

async def get_support_chat_id() -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'support_chat_id'") as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                try:
                    return int(row[0])
                except ValueError:
                    pass
    return CONFIG_SUPPORT_CHAT_ID

# ----------------- Робота з магазинами -----------------

async def create_shop(code: str, name: str) -> bool:
    code = code.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO shops (code, name) VALUES (?, ?)",
                (code, name.strip())
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_shop_by_code(code: str) -> Optional[Dict[str, Any]]:
    code = code.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shops WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_shop_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shops WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def register_shop(code: str, user_id: int, username: Optional[str], first_name: Optional[str]) -> Optional[Dict[str, Any]]:
    code = code.strip().lower()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shops WHERE code = ?", (code,)) as cursor:
            shop = await cursor.fetchone()
            if not shop:
                return None
            shop_dict = dict(shop)

        await db.execute("""
            UPDATE shops
            SET user_id = ?, username = ?, first_name = ?, registered_at = CURRENT_TIMESTAMP
            WHERE code = ?
        """, (user_id, username, first_name, code))
        await db.commit()
        shop_dict["user_id"] = user_id
        return shop_dict

async def get_all_shops() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shops ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_registered_shops() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shops WHERE user_id IS NOT NULL") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def save_message_link(group_message_id: int, shop_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages_map (group_message_id, shop_user_id) VALUES (?, ?)",
            (group_message_id, shop_user_id)
        )
        await db.commit()

async def get_shop_user_by_group_message(group_message_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT shop_user_id FROM messages_map WHERE group_message_id = ?",
            (group_message_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# ----------------- Робота з тікетами -----------------

async def create_ticket(
    shop_user_id: int,
    shop_name: str,
    dept_code: str,
    dept_name: str,
    group_message_id: int,
    shop_message_id: int,
    is_urgent: bool,
    message_text: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO tickets (
                shop_user_id, shop_name, dept_code, dept_name,
                group_message_id, shop_message_id, is_urgent, message_text, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (shop_user_id, shop_name, dept_code, dept_name, group_message_id, shop_message_id, 1 if is_urgent else 0, message_text))
        await db.commit()
        return cursor.lastrowid

async def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_ticket_by_group_message(group_message_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE group_message_id = ?", (group_message_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_ticket_status(ticket_id: int, status: str, worker_name: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "closed":
            await db.execute("""
                UPDATE tickets
                SET status = ?, worker_name = COALESCE(?, worker_name), closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, worker_name, ticket_id))
        else:
            await db.execute("""
                UPDATE tickets
                SET status = ?, worker_name = COALESCE(?, worker_name)
                WHERE id = ?
            """, (status, worker_name, ticket_id))
        await db.commit()

async def set_ticket_urgent(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET is_urgent = 1 WHERE id = ?", (ticket_id,))
        await db.commit()

async def rate_ticket(ticket_id: int, rating: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET rating = ? WHERE id = ?", (rating, ticket_id))
        await db.commit()

async def clear_all_shops_data():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM shops")
        await db.execute("DELETE FROM messages_map")
        await db.execute("DELETE FROM tickets")
        await db.commit()
