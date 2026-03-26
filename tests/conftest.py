import pytest
import aiosqlite
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
async def db():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row

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
            category TEXT DEFAULT 'other',
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
            category TEXT DEFAULT 'other',
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

    yield db

    await db.close()


@pytest.fixture
def admin_user():
    return {
        "telegram_id": 123456789,
        "username": "admin_user",
        "full_name": "Admin User",
    }


@pytest.fixture
def regular_user():
    return {
        "telegram_id": 987654321,
        "username": "regular_user",
        "full_name": "Regular User",
    }
