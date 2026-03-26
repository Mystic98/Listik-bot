# AGENTS.md

Guidelines for AI coding agents working on this Telegram grocery shopping bot.

## Build/Lint/Test Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Install dev dependencies
uv sync --all-extras

# Run the bot
uv run python bot.py

# Run all tests
uv run pytest

# Run all tests with coverage (default, requires 60% coverage)
uv run pytest --cov=. --cov-report=term-missing

# Run a single test file
uv run pytest tests/test_handlers.py

# Run a single test class
uv run pytest tests/test_handlers.py::TestHandlers

# Run a single test
uv run pytest tests/test_handlers.py::TestHandlers::test_cmd_start_new_user_pending

# Run tests with verbose output
uv run pytest -v

# Run tests with HTML coverage report
uv run pytest --cov-report=html

# Run tests without coverage requirement
uv run pytest --no-cov
```

## Project Structure

```
├── bot.py          # Entry point, bot initialization, error handler
├── config.py       # Environment configuration (BOT_TOKEN, ADMIN_ID, DATABASE_PATH)
├── database.py     # SQLite operations with aiosqlite
├── handlers.py     # All Telegram command/message/callback handlers
├── states.py       # FSM states for multi-step flows
├── utils.py        # Quantity parsing, formatting, unit conversion
└── tests/
    ├── conftest.py     # Shared fixtures (db, admin_user, regular_user)
    ├── test_database.py
    ├── test_handlers.py
    └── test_utils.py
```

## Code Style Guidelines

### Imports

```python
# Standard library first
import asyncio
import re
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple, Union

# Third-party next
import aiosqlite
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Local imports last (blank line before)
from config import ADMIN_ID
from database import get_db, add_item
from utils import format_item, combine_quantities
from states import AddProductStates
```

### Naming Conventions

- **Functions/variables**: `snake_case` - e.g., `get_pending_items`, `user_display`
- **Classes**: `PascalCase` - e.g., `AddProductStates`, `TestHandlers`
- **Constants**: `UPPER_SNAKE_CASE` - e.g., `BOT_TOKEN`, `ADMIN_ID`, `UNITS`
- **Private functions**: Prefix with underscore - e.g., `_init_tables()`
- **Handler functions**: Prefix with action - e.g., `cmd_start`, `btn_list_menu`, `callback_purchase`
- **FSM states**: `waiting_for_<what>` - e.g., `waiting_for_name`, `waiting_for_unit`

### Async Patterns

- Use `async with get_db() as db:` for database operations
- All database functions are async
- Use `AsyncMock` and `MagicMock` for testing async code

```python
# Database context manager pattern
async with get_db() as db:
    items = await get_pending_items(db)
    await add_item(db, name, quantity, user.id, user_display)
```

### Type Hints

Use type hints for function signatures:

```python
def get_user_display_name(user: types.User) -> str:
    ...

async def add_user(
    db: aiosqlite.Connection,
    telegram_id: int,
    username: Optional[str],
    full_name: str,
    added_by: int,
    approved: bool = True,
) -> None:
    ...

def combine_quantities(q1: Optional[str], q2: Optional[str]) -> Optional[str]:
    ...
```

### Error Handling

- Use try/except for message edits that may fail (message deleted, too old):
```python
try:
    await callback.message.edit_text(text, reply_markup=keyboard)
except:
    pass  # Message may have been deleted
```

- For user input validation, send error message and return early:
```python
if not message.text or not message.text.strip():
    await message.answer("❌ Название не может быть пустым.")
    return
```

### Telegram Bot Patterns

**Reply Keyboards:**
```python
def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📋 Список"), KeyboardButton(text="📋 Шаблоны")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
```

**Inline Keyboards:**
```python
keyboard = [
    [
        InlineKeyboardButton(text=f"✅ {i}", callback_data=f"purchase_{item['id']}"),
        InlineKeyboardButton(text=f"🗑 {i}", callback_data=f"remove_{item['id']}"),
    ]
]
await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
```

**FSM State Management:**
```python
# Set state
await state.set_state(AddProductStates.waiting_for_name)

# Store data
await state.update_data(product_name=name)

# Retrieve data
data = await state.get_data()
name = data.get("product_name")

# Clear state
await state.clear()
```

**Callback Query Response:**
```python
@router.callback_query(F.data.startswith("purchase_"))
async def callback_purchase(callback: types.CallbackQuery):
    # ... business logic ...
    await callback.answer("✅ Отмечено как купленное")  # Popup notification
```

## Testing Conventions

### Test Structure

```python
class TestHandlers:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.answer = AsyncMock()
        return message

    @pytest.mark.asyncio
    async def test_cmd_start_new_user(self, mock_message):
        # Arrange
        with patch("handlers.check_access", return_value=True):
            # Act
            from handlers import cmd_start
            await cmd_start(mock_message)
            
            # Assert
            mock_message.answer.assert_called_once()
```

### Async Context Manager Helper

```python
def make_async_context_manager(return_value):
    cm = AsyncMock()
    cm.__aenter__.return_value = return_value
    cm.__aexit__.return_value = None
    return cm

# Usage
with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
    ...
```

### Database Fixture

Tests use in-memory SQLite:
```python
@pytest.fixture
async def db():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    # ... create tables ...
    yield db
    await db.close()
```

## Business Logic Notes

### Unit Groups

Products are grouped for combining quantities:
- **Weight**: кг, г (kg, g)
- **Volume**: л, мл (l, ml)  
- **Pieces**: шт, уп, or no unit

Same product with same unit group = quantities combined (e.g., "молоко 2л" + "молоко 500мл" = "молоко 2.5л")

### Cyrillic Case Sensitivity

SQLite's `LOWER()` doesn't handle Cyrillic. Use Python's `.lower()` for case-insensitive comparisons:
```python
if item["name"].lower() == other_item["name"].lower():
    ...
```

### Access Control

1. New users → pending list (not approved)
2. Admin sees pending via `/pending` command
3. Admin approves/rejects via inline buttons
4. Only approved users can use bot features

## Key Files to Modify

- **New command**: Add to `handlers.py`, add tests to `test_handlers.py`
- **New database field**: Update `database.py` schema, update tests
- **New unit type**: Update `utils.py` `UNITS` list and `get_unit_group()`
- **New FSM flow**: Add state class to `states.py`, handlers to `handlers.py`
