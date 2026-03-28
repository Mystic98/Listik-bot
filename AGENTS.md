# AGENTS.md

Guidelines for AI coding agents working on this Telegram grocery shopping bot.

## Build/Lint/Test Commands

```bash
uv sync                          # Install dependencies
uv run python bot.py             # Run the bot

uv run pytest                    # Run all tests (requires 60% coverage)
uv run pytest --no-cov           # Run tests without coverage check
uv run pytest -v                 # Verbose output
uv run pytest --cov-report=html  # HTML coverage report

uv run pytest tests/test_handlers.py                           # Single file
uv run pytest tests/test_handlers.py::TestHandlers             # Single class
uv run pytest tests/test_handlers.py::TestHandlers::test_cmd_start_new_user_pending  # Single test
```

## Project Structure

```
├── bot.py          # Entry point, error handler, weekly reminder scheduler
├── config.py       # pydantic-settings: bot_token, admin_id, database_path
├── database.py     # SQLite + aiosqlite, all DB functions (~985 lines)
├── handlers.py     # All Telegram handlers + helper functions (~3000 lines)
├── models.py       # pydantic models: User, Item, Template, TemplateItem, Room, RoomMember
├── states.py       # FSM state groups: AddProduct, EditProduct, Template, Room
├── utils.py        # parse_amount, is_valid_unit, build_quantity, format_item, etc.
├── categories.py   # 13 categories, keyword dict, fuzzy matching, categorize_product()
└── tests/
    ├── conftest.py       # Shared fixtures, make_async_context_manager helper
    ├── test_handlers.py  # TestHandlers, TestTemplates, TestTemplateFSM, TestRoomHandlers
    ├── test_database.py
    ├── test_categories.py
    └── test_utils.py
```

## Code Style

### Imports

Standard library → third-party → local (blank line before local). One import per line for local modules:
```python
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from config import settings
from database import get_db, add_item
from utils import format_item, combine_quantities
from states import AddProductStates, RoomStates
from categories import categorize_product, get_all_categories
```

### Naming

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private functions**: prefix `_` — `_init_tables()`
- **Handlers**: prefix by trigger type — `cmd_start`, `btn_list_menu`, `callback_purchase`, `process_room_name`
- **FSM states**: `waiting_for_<what>` — `waiting_for_name`, `waiting_for_room_name`
- **Keyboard builders**: `get_<name>_keyboard()` — `get_main_keyboard()`, `get_room_keyboard()`
- **Message builders**: `build_<name>_message()` — `build_list_message()`, `build_templates_message()`

### No Comments

Do not add comments to code unless explicitly asked.

### Type Hints

All function signatures must have type hints:
```python
async def add_item(db: aiosqlite.Connection, name: str, quantity: Optional[str],
                   added_by: int, added_by_name: str, category: str = "other",
                   room_id: Optional[int] = None) -> int:
```

### Error Handling

- Use `except Exception:` (never bare `except:`)
- Silent catch only for Telegram message edits that may fail (deleted/too old):
```python
try:
    await callback.message.edit_text(text, reply_markup=keyboard)
except Exception:
    pass
```
- For user input: validate, send error message, return early

## Architecture

### Multi-Room System

All data (items, templates) is scoped by `room_id`. Most DB functions accept `room_id: Optional[int] = None`.

**Access flow:** Global admin approval → room membership. `require_room(message, state)` guard checks for active room before list/template operations.

**Room keyboard** (`get_room_keyboard(is_creator)`): Invite, Members, Rename/Delete (creator only), Leave (member only).

### Access Control

1. New user `/start` → pending list
2. Admin `/pending` → approve/reject via inline buttons
3. Approved users can create/join rooms
4. Room invite checks: user exists AND `is_approved = TRUE` (via `get_user_by_username`)

### Database Patterns

- All DB functions are async, use `async with get_db() as db:`
- DB functions return pydantic models (User, Item, TemplateWithCount, etc.)
- `CATEGORIES` dict in `categories.py` is static config — `all_cats[cat_id]["name"]` is correct as-is

### Cyrillic Case Sensitivity

SQLite's `LOWER()` doesn't handle Cyrillic. Use Python's `.lower()` for comparisons.

### Key Pitfalls

- `state.clear()` wipes ALL state data — save `room_id` before clearing if needed
- `F.data.startswith("edit_")` matches both `edit_1` and `edit_template_item_1` — use `F.data.regexp(r"^edit_\d+$")` for precise matching
- When adding items from templates, pass `room_id` to `add_item` and `get_pending_items`
- `get_user_by_username` filters `is_approved = TRUE`; use `get_user_by_username_all` to check pending users

## Testing Patterns

```python
class TestRoomHandlers:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        message.delete = AsyncMock()
        return message

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        return state

    @pytest.mark.asyncio
    async def test_something(self, mock_message, mock_state):
        with patch("handlers.check_access", return_value=True):
            with patch("handlers.require_room", return_value=True):
                with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
                    ...
```

Use `make_async_context_manager(mock_db)` to mock `get_db()`. For handlers that call `require_room`, mock it to return `True` to skip room checks.
