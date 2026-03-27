import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import settings
from models import User, Item, Template, TemplateWithCount, TemplateItem
from utils import extract_quantity_parts, get_unit_group


async def _init_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            added_by INTEGER,
            is_approved BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity TEXT,
            added_by INTEGER NOT NULL,
            added_by_name TEXT,
            is_purchased BOOLEAN DEFAULT FALSE,
            purchased_by INTEGER,
            purchased_by_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            purchased_at DATETIME
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS product_categories (
            name TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.commit()

    try:
        await db.execute(
            "ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT FALSE"
        )
        await db.commit()
    except Exception:
        pass

    try:
        await db.execute(
            "UPDATE users SET is_approved = TRUE WHERE is_approved IS NULL"
        )
        await db.commit()
    except Exception:
        pass

    try:
        await db.execute("ALTER TABLE items ADD COLUMN category TEXT DEFAULT 'other'")
        await db.commit()
    except Exception:
        pass

    try:
        await db.execute(
            "ALTER TABLE template_items ADD COLUMN category TEXT DEFAULT 'other'"
        )
        await db.commit()
    except Exception:
        pass

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_is_purchased ON items(is_purchased)"
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_template_items_template_id ON template_items(template_id)"
    )
    await db.commit()


@asynccontextmanager
async def get_db(db_path: str = None):
    if db_path is None:
        db_path = settings.database_path
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await _init_tables(db)
    try:
        yield db
    finally:
        await db.close()


async def add_user(
    db: aiosqlite.Connection,
    telegram_id: int,
    username: Optional[str],
    full_name: str,
    added_by: int,
    approved: bool = True,
) -> None:
    await db.execute(
        """
        INSERT OR REPLACE INTO users (telegram_id, username, full_name, added_by, is_approved)
        VALUES (?, ?, ?, ?, ?)
        """,
        (telegram_id, username, full_name, added_by, approved),
    )
    await db.commit()


async def add_pending_user(
    db: aiosqlite.Connection,
    telegram_id: int,
    username: Optional[str],
    full_name: str,
) -> None:
    await add_user(db, telegram_id, username, full_name, telegram_id, approved=False)


async def approve_user(db: aiosqlite.Connection, telegram_id: int) -> bool:
    cursor = await db.execute(
        "UPDATE users SET is_approved = TRUE WHERE telegram_id = ?",
        (telegram_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def reject_user(db: aiosqlite.Connection, telegram_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM users WHERE telegram_id = ? AND is_approved = FALSE",
        (telegram_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_user_by_telegram_id(
    db: aiosqlite.Connection, telegram_id: int
) -> Optional[User]:
    cursor = await db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    )
    row = await cursor.fetchone()
    return User.model_validate(dict(row)) if row else None


async def get_user_by_username(
    db: aiosqlite.Connection, username: str
) -> Optional[User]:
    if username.startswith("@"):
        username = username[1:]

    cursor = await db.execute(
        "SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND is_approved = TRUE",
        (username,),
    )
    row = await cursor.fetchone()
    return User.model_validate(dict(row)) if row else None


async def get_user_by_username_all(
    db: aiosqlite.Connection, username: str
) -> Optional[User]:
    if username.startswith("@"):
        username = username[1:]

    cursor = await db.execute(
        "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
        (username,),
    )
    row = await cursor.fetchone()
    return User.model_validate(dict(row)) if row else None


async def is_user_allowed(db: aiosqlite.Connection, telegram_id: int) -> bool:
    cursor = await db.execute(
        "SELECT is_approved FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = await cursor.fetchone()
    return row is not None and row["is_approved"] == 1


async def remove_user(db: aiosqlite.Connection, telegram_id: int) -> bool:
    cursor = await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    await db.commit()
    return cursor.rowcount > 0


async def get_all_users(db: aiosqlite.Connection) -> List[User]:
    cursor = await db.execute(
        "SELECT * FROM users WHERE is_approved = TRUE ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    return [User.model_validate(dict(row)) for row in rows]


async def get_pending_users(db: aiosqlite.Connection) -> List[User]:
    cursor = await db.execute(
        "SELECT * FROM users WHERE is_approved = FALSE ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    return [User.model_validate(dict(row)) for row in rows]


async def get_approved_telegram_ids(db: aiosqlite.Connection) -> List[int]:
    cursor = await db.execute("SELECT telegram_id FROM users WHERE is_approved = TRUE")
    rows = await cursor.fetchall()
    return [row["telegram_id"] for row in rows]


async def add_item(
    db: aiosqlite.Connection,
    name: str,
    quantity: Optional[str],
    added_by: int,
    added_by_name: str,
    category: str = "other",
) -> int:
    cursor = await db.execute(
        """
        INSERT INTO items (name, quantity, added_by, added_by_name, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, quantity, added_by, added_by_name, category),
    )
    await db.commit()
    return cursor.lastrowid


async def get_all_items(db: aiosqlite.Connection) -> List[Item]:
    cursor = await db.execute("SELECT * FROM items ORDER BY created_at")
    rows = await cursor.fetchall()
    return [Item.model_validate(dict(row)) for row in rows]


async def get_pending_items(db: aiosqlite.Connection) -> List[Item]:
    cursor = await db.execute(
        "SELECT * FROM items WHERE is_purchased = FALSE ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    return [Item.model_validate(dict(row)) for row in rows]


async def get_purchased_items(db: aiosqlite.Connection) -> List[Item]:
    cursor = await db.execute(
        "SELECT * FROM items WHERE is_purchased = TRUE ORDER BY purchased_at DESC"
    )
    rows = await cursor.fetchall()
    return [Item.model_validate(dict(row)) for row in rows]


async def get_item_by_id(db: aiosqlite.Connection, item_id: int) -> Optional[Item]:
    cursor = await db.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = await cursor.fetchone()
    return Item.model_validate(dict(row)) if row else None


async def mark_as_purchased(
    db: aiosqlite.Connection, item_id: int, purchased_by: int, purchased_by_name: str
) -> bool:
    cursor = await db.execute(
        """
        UPDATE items 
        SET is_purchased = TRUE, 
            purchased_by = ?, 
            purchased_by_name = ?,
            purchased_at = CURRENT_TIMESTAMP
        WHERE id = ? AND is_purchased = FALSE
        """,
        (purchased_by, purchased_by_name, item_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def unmark_purchased(db: aiosqlite.Connection, item_id: int) -> bool:
    cursor = await db.execute(
        """
        UPDATE items 
        SET is_purchased = FALSE, 
            purchased_by = NULL, 
            purchased_by_name = NULL,
            purchased_at = NULL
        WHERE id = ? AND is_purchased = TRUE
        """,
        (item_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def remove_item(db: aiosqlite.Connection, item_id: int) -> bool:
    cursor = await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    await db.commit()
    return cursor.rowcount > 0


async def find_pending_item_by_name_and_unit(
    db: aiosqlite.Connection, name: str, unit: str
) -> Optional[Item]:
    cursor = await db.execute("SELECT * FROM items WHERE is_purchased = FALSE")
    rows = await cursor.fetchall()

    name_lower = name.lower()
    unit_lower = unit.lower() if unit else ""

    for row in rows:
        item = Item.model_validate(dict(row))
        if item.name.lower() == name_lower and item.quantity:
            _, row_unit = extract_quantity_parts(item.quantity)
            if row_unit == unit_lower:
                return item
    return None


async def find_pending_item_by_name(
    db: aiosqlite.Connection, name: str, quantity: Optional[str] = None
) -> Optional[Item]:
    cursor = await db.execute("SELECT * FROM items WHERE is_purchased = FALSE")
    rows = await cursor.fetchall()

    name_lower = name.lower()

    for row in rows:
        item = Item.model_validate(dict(row))
        if item.name.lower() == name_lower and item.quantity is None:
            return item
    return None


async def find_pending_item_in_unit_group(
    db: aiosqlite.Connection, name: str, group: str
) -> Optional[Item]:
    cursor = await db.execute("SELECT * FROM items WHERE is_purchased = FALSE")
    rows = await cursor.fetchall()

    name_lower = name.lower()

    for row in rows:
        item = Item.model_validate(dict(row))
        if item.name.lower() == name_lower:
            row_unit = (
                extract_quantity_parts(item.quantity)[1] if item.quantity else None
            )
            row_group = get_unit_group(row_unit)
            if row_group == group:
                return item
    return None


async def update_item_quantity(
    db: aiosqlite.Connection, item_id: int, new_quantity: Optional[str]
) -> bool:
    cursor = await db.execute(
        "UPDATE items SET quantity = ? WHERE id = ?",
        (new_quantity, item_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_all_items_ordered(db: aiosqlite.Connection) -> List[Item]:
    cursor = await db.execute(
        """
        SELECT * FROM items 
        ORDER BY 
            is_purchased ASC,
            CASE category
                WHEN 'dairy' THEN 1
                WHEN 'meat' THEN 2
                WHEN 'fish' THEN 3
                WHEN 'vegetables' THEN 4
                WHEN 'fruits' THEN 5
                WHEN 'bakery' THEN 6
                WHEN 'grocery' THEN 7
                WHEN 'frozen' THEN 8
                WHEN 'canned' THEN 9
                WHEN 'drinks' THEN 10
                WHEN 'sweets' THEN 11
                WHEN 'household' THEN 12
                ELSE 99
            END,
            created_at
        """
    )
    rows = await cursor.fetchall()
    return [Item.model_validate(dict(row)) for row in rows]


async def clear_purchased_items(db: aiosqlite.Connection) -> int:
    cursor = await db.execute("DELETE FROM items WHERE is_purchased = TRUE")
    await db.commit()
    return cursor.rowcount


async def create_template(db: aiosqlite.Connection, name: str) -> int:
    cursor = await db.execute(
        "INSERT INTO templates (name) VALUES (?)",
        (name,),
    )
    await db.commit()
    return cursor.lastrowid


async def get_all_templates(db: aiosqlite.Connection) -> List[TemplateWithCount]:
    cursor = await db.execute(
        """
        SELECT t.*, COUNT(ti.id) as item_count
        FROM templates t
        LEFT JOIN template_items ti ON t.id = ti.template_id
        GROUP BY t.id
        ORDER BY t.created_at
        """
    )
    rows = await cursor.fetchall()
    return [TemplateWithCount.model_validate(dict(row)) for row in rows]


async def get_template_by_id(
    db: aiosqlite.Connection, template_id: int
) -> Optional[Template]:
    cursor = await db.execute(
        "SELECT * FROM templates WHERE id = ?",
        (template_id,),
    )
    row = await cursor.fetchone()
    return Template.model_validate(dict(row)) if row else None


async def get_template_by_name(
    db: aiosqlite.Connection, name: str
) -> Optional[Template]:
    cursor = await db.execute("SELECT * FROM templates")
    rows = await cursor.fetchall()

    name_lower = name.lower()
    for row in rows:
        template = Template.model_validate(dict(row))
        if template.name.lower() == name_lower:
            return template
    return None


async def delete_template(db: aiosqlite.Connection, template_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM templates WHERE id = ?",
        (template_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def rename_template(
    db: aiosqlite.Connection, template_id: int, new_name: str
) -> bool:
    try:
        cursor = await db.execute(
            "UPDATE templates SET name = ? WHERE id = ?",
            (new_name, template_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


async def add_item_to_template(
    db: aiosqlite.Connection,
    template_id: int,
    name: str,
    quantity: Optional[str],
    category: str = "other",
) -> int:
    cursor = await db.execute(
        "INSERT INTO template_items (template_id, name, quantity, category) VALUES (?, ?, ?, ?)",
        (template_id, name, quantity, category),
    )
    await db.commit()
    return cursor.lastrowid


async def get_template_items(
    db: aiosqlite.Connection, template_id: int
) -> List[TemplateItem]:
    cursor = await db.execute(
        "SELECT * FROM template_items WHERE template_id = ? ORDER BY created_at",
        (template_id,),
    )
    rows = await cursor.fetchall()
    return [TemplateItem.model_validate(dict(row)) for row in rows]


async def get_template_item_by_id(
    db: aiosqlite.Connection, item_id: int
) -> Optional[TemplateItem]:
    cursor = await db.execute(
        "SELECT * FROM template_items WHERE id = ?",
        (item_id,),
    )
    row = await cursor.fetchone()
    return TemplateItem.model_validate(dict(row)) if row else None


async def remove_template_item(db: aiosqlite.Connection, item_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM template_items WHERE id = ?",
        (item_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_template_item(
    db: aiosqlite.Connection, item_id: int, new_quantity: Optional[str]
) -> bool:
    cursor = await db.execute(
        "UPDATE template_items SET quantity = ? WHERE id = ?",
        (new_quantity, item_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def create_template_from_items(
    db: aiosqlite.Connection, name: str, items: List[Item]
) -> int:
    template_id = await create_template(db, name)
    for item in items:
        await add_item_to_template(
            db,
            template_id,
            item.name,
            item.quantity,
            item.category,
        )
    return template_id


async def find_template_item_in_unit_group(
    db: aiosqlite.Connection, template_id: int, name: str, group: str
) -> Optional[TemplateItem]:
    items = await get_template_items(db, template_id)
    name_lower = name.lower()

    for item in items:
        if item.name.lower() == name_lower:
            item_unit = (
                extract_quantity_parts(item.quantity)[1] if item.quantity else None
            )
            item_group = get_unit_group(item_unit)
            if item_group == group:
                return item
    return None


async def update_item_category(
    db: aiosqlite.Connection, item_id: int, category: str
) -> bool:
    cursor = await db.execute(
        "UPDATE items SET category = ? WHERE id = ?",
        (category, item_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_template_item_category(
    db: aiosqlite.Connection, item_id: int, category: str
) -> bool:
    cursor = await db.execute(
        "UPDATE template_items SET category = ? WHERE id = ?",
        (category, item_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def save_product_category(
    db: aiosqlite.Connection, name: str, category: str
) -> None:
    await db.execute(
        """
        INSERT OR REPLACE INTO product_categories (name, category, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        """,
        (name.lower(), category),
    )
    await db.commit()


async def get_product_category(db: aiosqlite.Connection, name: str) -> Optional[str]:
    cursor = await db.execute(
        "SELECT category FROM product_categories WHERE name = ?",
        (name.lower(),),
    )
    row = await cursor.fetchone()
    return row["category"] if row else None


async def get_all_product_categories(
    db: aiosqlite.Connection,
) -> Dict[str, str]:
    cursor = await db.execute("SELECT name, category FROM product_categories")
    rows = await cursor.fetchall()
    return {row["name"]: row["category"] for row in rows}


async def get_pending_items_ordered(
    db: aiosqlite.Connection,
) -> List[Item]:
    cursor = await db.execute(
        """
        SELECT * FROM items 
        WHERE is_purchased = FALSE 
        ORDER BY 
            CASE category
                WHEN 'dairy' THEN 1
                WHEN 'meat' THEN 2
                WHEN 'fish' THEN 3
                WHEN 'vegetables' THEN 4
                WHEN 'fruits' THEN 5
                WHEN 'bakery' THEN 6
                WHEN 'grocery' THEN 7
                WHEN 'frozen' THEN 8
                WHEN 'canned' THEN 9
                WHEN 'drinks' THEN 10
                WHEN 'sweets' THEN 11
                WHEN 'household' THEN 12
                ELSE 99
            END,
            created_at
        """
    )
    rows = await cursor.fetchall()
    return [Item.model_validate(dict(row)) for row in rows]


async def get_template_items_ordered(
    db: aiosqlite.Connection, template_id: int
) -> List[TemplateItem]:
    cursor = await db.execute(
        """
        SELECT * FROM template_items 
        WHERE template_id = ?
        ORDER BY 
            CASE category
                WHEN 'dairy' THEN 1
                WHEN 'meat' THEN 2
                WHEN 'fish' THEN 3
                WHEN 'vegetables' THEN 4
                WHEN 'fruits' THEN 5
                WHEN 'bakery' THEN 6
                WHEN 'grocery' THEN 7
                WHEN 'frozen' THEN 8
                WHEN 'canned' THEN 9
                WHEN 'drinks' THEN 10
                WHEN 'sweets' THEN 11
                WHEN 'household' THEN 12
                ELSE 99
            END,
            created_at
        """,
        (template_id,),
    )
    rows = await cursor.fetchall()
    return [TemplateItem.model_validate(dict(row)) for row in rows]
