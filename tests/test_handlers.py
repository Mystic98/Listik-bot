import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, Item, Template, TemplateWithCount, TemplateItem


def make_async_context_manager(return_value):
    cm = AsyncMock()
    cm.__aenter__.return_value = return_value
    cm.__aexit__.return_value = None
    return cm


def make_user(
    telegram_id=111222333,
    username="test_user",
    full_name="Test User",
    is_approved=False,
):
    return User(
        id=1,
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        added_by=1,
        is_approved=is_approved,
    )


def make_item(
    id=1,
    name="Test Item",
    quantity="1шт",
    added_by=123456,
    added_by_name="Test User",
    category="other",
    is_purchased=False,
):
    return Item(
        id=id,
        name=name,
        quantity=quantity if quantity else None,
        added_by=added_by,
        added_by_name=added_by_name,
        is_purchased=is_purchased,
        category=category,
    )


def make_template(id=1, name="Test Template", item_count=0):
    return TemplateWithCount(
        id=id,
        name=name,
        item_count=item_count,
    )


def make_template_item(
    id=1, template_id=1, name="Test Item", quantity="1шт", category="other"
):
    return TemplateItem(
        id=id,
        template_id=template_id,
        name=name,
        quantity=quantity if quantity else None,
        category=category,
    )


class TestHandlers:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        message.reply_to_message = None
        message.edit_text = AsyncMock()
        message.bot = AsyncMock()
        return message

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        return state

    @pytest.fixture
    def mock_callback(self):
        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123456
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.data = ""
        callback.answer = AsyncMock()
        callback.message = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.message.from_user = MagicMock()
        callback.message.from_user.id = 123456
        callback.message.from_user.username = "test_user"
        callback.message.from_user.full_name = "Test User"
        callback.message.text = ""
        callback.bot = AsyncMock()
        return callback

    @pytest.mark.asyncio
    async def test_cmd_start_new_user_pending(self, mock_message):
        mock_db = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_user_by_telegram_id", return_value=None):
                with patch("handlers.add_pending_user", AsyncMock()):
                    with patch("handlers.settings.admin_id", 999999):
                        from handlers import cmd_start

                        mock_message.from_user.id = 111222333
                        await cmd_start(mock_message)

                        mock_message.answer.assert_called_once()
                        call_args = mock_message.answer.call_args[0][0]
                        assert "запрос на доступ отправлен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_start_pending_user_waiting(self, mock_message):
        mock_db = AsyncMock()
        existing_user = make_user(telegram_id=111222333, is_approved=False)

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_user_by_telegram_id", return_value=existing_user):
                with patch("handlers.settings.admin_id", 999999):
                    from handlers import cmd_start

                    mock_message.from_user.id = 111222333
                    await cmd_start(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Ожидайте подтверждения" in call_args

    @pytest.mark.asyncio
    async def test_cmd_start_admin_user(self, mock_message):
        mock_db = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_user_by_telegram_id", return_value=None):
                with patch("handlers.add_user", AsyncMock()):
                    with patch("handlers.settings.admin_id", 123456):
                        from handlers import cmd_start

                        mock_message.from_user.id = 123456
                        await cmd_start(mock_message)

                        mock_message.answer.assert_called_once()
                        call_args = mock_message.answer.call_args[0][0]
                        assert "Добро пожаловать" in call_args

    @pytest.mark.asyncio
    async def test_cmd_start_authorized_user(self, mock_message):
        mock_db = AsyncMock()
        existing_user = make_user(telegram_id=111222333, is_approved=True)

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_user_by_telegram_id", return_value=existing_user):
                with patch("handlers.settings.admin_id", 999999):
                    from handlers import cmd_start

                    mock_message.from_user.id = 111222333
                    await cmd_start(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Привет" in call_args

    @pytest.mark.asyncio
    async def test_cmd_add_starts_fsm(self, mock_message, mock_state):
        with patch("handlers.check_access", return_value=True):
            from handlers import cmd_add

            mock_message.text = "/add"
            await cmd_add(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "название продукта" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_add_with_text(self, mock_message, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group", return_value=None
                ):
                    with patch("handlers.add_item", AsyncMock()) as mock_add:
                        from handlers import cmd_add

                        mock_message.text = "/add молоко 2л"
                        await cmd_add(mock_message, mock_state)

                        mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_unauthorized(self, mock_message, mock_state):
        with patch("handlers.check_access", return_value=False):
            from handlers import cmd_add

            mock_message.text = "/add молоко"
            await cmd_add(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "⛔ Доступ запрещён" in call_args

    @pytest.mark.asyncio
    async def test_cmd_list_empty(self, mock_message, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_items_ordered", return_value=[]):
                    from handlers import btn_list_menu

                    await btn_list_menu(mock_message, mock_state)

                    assert mock_message.answer.call_count >= 1
                    call_args = mock_message.answer.call_args_list[0][0][0]
                    assert "пуст" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_list_with_items(self, mock_message, mock_state):
        items = [
            make_item(
                id=1,
                name="молоко",
                quantity="2л",
                added_by_name="User1",
                category="dairy",
            ),
            make_item(
                id=2,
                name="хлеб",
                quantity=None,
                added_by_name="User2",
                category="bakery",
            ),
        ]
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_items_ordered", return_value=items):
                    from handlers import btn_list_menu

                    await btn_list_menu(mock_message, mock_state)

                    assert mock_message.answer.call_count >= 1
                    call_args = mock_message.answer.call_args_list[0][0][0]
                    assert "молоко" in call_args
                    assert "хлеб" in call_args

    @pytest.mark.asyncio
    async def test_cmd_list_unauthorized(self, mock_message, mock_state):
        with patch("handlers.check_access", return_value=False):
            from handlers import btn_list_menu

            await btn_list_menu(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "⛔ Доступ запрещён" in call_args

    @pytest.mark.asyncio
    async def test_cmd_done_success(self, mock_message):
        items = [make_item(id=1, name="молоко", quantity="2л")]
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_items_ordered", return_value=items):
                    with patch("handlers.mark_as_purchased", return_value=True):
                        from handlers import cmd_done

                        mock_message.text = "/done 1"
                        await cmd_done(mock_message)

                        mock_message.answer.assert_called_once()
                        call_args = mock_message.answer.call_args[0][0]
                        assert "✅ Куплено" in call_args

    @pytest.mark.asyncio
    async def test_cmd_clear_success(self, mock_message, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.clear_purchased_items", return_value=3
                ) as mock_clear:
                    with patch(
                        "handlers.build_list_message", return_value=("Список", None)
                    ):
                        from handlers import cmd_clear

                        await cmd_clear(mock_message, mock_state)

                        mock_clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_allow_not_admin(self, mock_message):
        with patch("handlers.settings.admin_id", 999999):
            from handlers import cmd_allow

            mock_message.from_user.id = 123456
            mock_message.text = "/allow @user"
            await cmd_allow(mock_message)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "только администратор" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_allow_by_username_pending(self, mock_message):
        mock_db = AsyncMock()
        target_user = make_user(
            telegram_id=987654, username="target", is_approved=False
        )

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.get_user_by_username_all", return_value=target_user
                ):
                    with patch("handlers.approve_user", return_value=True):
                        from handlers import cmd_allow

                        mock_message.from_user.id = 123456
                        mock_message.text = "/allow @target"
                        await cmd_allow(mock_message)

                        mock_message.answer.assert_called_once()
                        call_args = mock_message.answer.call_args[0][0]
                        assert "Доступ разрешён" in call_args

    @pytest.mark.asyncio
    async def test_cmd_allow_by_username_not_found(self, mock_message):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_user_by_username_all", return_value=None):
                    from handlers import cmd_allow

                    mock_message.from_user.id = 123456
                    mock_message.text = "/allow @nonexistent"
                    await cmd_allow(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "не найден" in call_args

    @pytest.mark.asyncio
    async def test_cmd_allow_already_approved(self, mock_message):
        mock_db = AsyncMock()
        target_user = make_user(telegram_id=987654, username="target", is_approved=True)

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.get_user_by_username_all", return_value=target_user
                ):
                    from handlers import cmd_allow

                    mock_message.from_user.id = 123456
                    mock_message.text = "/allow @target"
                    await cmd_allow(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "уже имеет доступ" in call_args

    @pytest.mark.asyncio
    async def test_cmd_pending_empty(self, mock_message):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_pending_users", return_value=[]):
                    from handlers import cmd_pending

                    mock_message.from_user.id = 123456
                    await cmd_pending(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Нет ожидающих" in call_args

    @pytest.mark.asyncio
    async def test_cmd_pending_with_users(self, mock_message):
        mock_db = AsyncMock()
        pending_users = [
            make_user(telegram_id=111, username="user1", full_name="User One"),
            make_user(telegram_id=222, username=None, full_name="User Two"),
        ]

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_pending_users", return_value=pending_users):
                    from handlers import cmd_pending

                    mock_message.from_user.id = 123456
                    await cmd_pending(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Ожидающие подтверждения" in call_args
                    assert "user1" in call_args

    @pytest.mark.asyncio
    async def test_cmd_pending_not_admin(self, mock_message):
        with patch("handlers.settings.admin_id", 999999):
            from handlers import cmd_pending

            mock_message.from_user.id = 123456
            await cmd_pending(mock_message)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "только администратор" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_approve_success(self, mock_callback):
        mock_db = AsyncMock()
        target_user = {
            "telegram_id": 987654,
            "username": "target",
            "is_approved": False,
        }

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.get_user_by_telegram_id", return_value=target_user
                ):
                    with patch("handlers.approve_user", return_value=True):
                        with patch(
                            "handlers.build_pending_message",
                            return_value=("text", None),
                        ):
                            from handlers import callback_approve

                            mock_callback.from_user.id = 123456
                            mock_callback.data = "approve_987654"
                            await callback_approve(mock_callback)

                            mock_callback.answer.assert_called_once()
                            call_args = mock_callback.answer.call_args[0][0]
                            assert "одобрен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_approve_not_admin(self, mock_callback):
        with patch("handlers.settings.admin_id", 999999):
            from handlers import callback_approve

            mock_callback.from_user.id = 123456
            mock_callback.data = "approve_987654"
            await callback_approve(mock_callback)

            mock_callback.answer.assert_called_once()
            call_args = mock_callback.answer.call_args[0][0]
            assert "только администратор" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_reject_success(self, mock_callback):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.reject_user", return_value=True):
                    with patch(
                        "handlers.build_pending_message", return_value=("text", None)
                    ):
                        from handlers import callback_reject

                        mock_callback.from_user.id = 123456
                        mock_callback.data = "reject_987654"
                        await callback_reject(mock_callback)

                        mock_callback.answer.assert_called_once()
                        call_args = mock_callback.answer.call_args[0][0]
                        assert "отклонён" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_reject_not_admin(self, mock_callback):
        with patch("handlers.settings.admin_id", 999999):
            from handlers import callback_reject

            mock_callback.from_user.id = 123456
            mock_callback.data = "reject_987654"
            await callback_reject(mock_callback)

            mock_callback.answer.assert_called_once()
            call_args = mock_callback.answer.call_args[0][0]
            assert "только администратор" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_purchase_success(self, mock_callback):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.mark_as_purchased", return_value=True):
                    with patch(
                        "handlers.build_list_message", return_value=("text", None)
                    ):
                        from handlers import callback_purchase

                        mock_callback.data = "purchase_1"
                        await callback_purchase(mock_callback)

                        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_remove_success(self, mock_callback):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.remove_item", return_value=True):
                    with patch(
                        "handlers.build_list_message", return_value=("text", None)
                    ):
                        from handlers import callback_remove

                        mock_callback.data = "remove_1"
                        await callback_remove(mock_callback)

                        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_users_not_admin(self, mock_message):
        with patch("handlers.settings.admin_id", 999999):
            from handlers import cmd_users

            mock_message.from_user.id = 123456
            await cmd_users(mock_message)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "только администратор" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cmd_users_empty(self, mock_message):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 123456):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_users", return_value=[]):
                    from handlers import cmd_users

                    mock_message.from_user.id = 123456
                    await cmd_users(mock_message)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "пуст" in call_args.lower()


class TestGetUserDisplayName:
    def test_with_username(self):
        from handlers import get_user_display_name

        user = MagicMock()
        user.username = "test_user"
        user.full_name = "Test User"
        user.id = 123456

        result = get_user_display_name(user)
        assert result == "@test_user"

    def test_without_username(self):
        from handlers import get_user_display_name

        user = MagicMock()
        user.username = None
        user.full_name = "Test User"
        user.id = 123456

        result = get_user_display_name(user)
        assert result == "Test User"

    def test_without_username_and_fullname(self):
        from handlers import get_user_display_name

        user = MagicMock()
        user.username = None
        user.full_name = None
        user.id = 123456

        result = get_user_display_name(user)
        assert result == "123456"


class TestCheckAccess:
    @pytest.mark.asyncio
    async def test_check_access_admin(self):
        with patch("handlers.settings.admin_id", 123456):
            from handlers import check_access

            result = await check_access(123456)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_access_allowed_user(self):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 999999):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.is_user_allowed", return_value=True):
                    from handlers import check_access

                    result = await check_access(123456)
                    assert result is True

    @pytest.mark.asyncio
    async def test_check_access_not_allowed(self):
        mock_db = AsyncMock()

        with patch("handlers.settings.admin_id", 999999):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.is_user_allowed", return_value=False):
                    from handlers import check_access

                    result = await check_access(123456)
                    assert result is False


class TestCombineQuantitiesIntegration:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        message.reply_to_message = None
        message.edit_text = AsyncMock()
        message.bot = AsyncMock()
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
    async def test_cmd_add_combine_kg_and_grams(self, mock_message, mock_state):
        mock_db = AsyncMock()
        existing_item = make_item(id=1, name="сыр", quantity="1кг")

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group",
                    return_value=existing_item,
                ):
                    with patch(
                        "handlers.update_item_quantity", return_value=True
                    ) as mock_update:
                        from handlers import cmd_add

                        mock_message.text = "/add сыр 200г"
                        await cmd_add(mock_message, mock_state)

                        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_combine_liters_and_ml(self, mock_message, mock_state):
        mock_db = AsyncMock()
        existing_item = make_item(id=1, name="молоко", quantity="1л")

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group",
                    return_value=existing_item,
                ):
                    with patch(
                        "handlers.update_item_quantity", return_value=True
                    ) as mock_update:
                        from handlers import cmd_add

                        mock_message.text = "/add молоко 500мл"
                        await cmd_add(mock_message, mock_state)

                        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_combine_pieces_none(self, mock_message, mock_state):
        mock_db = AsyncMock()
        existing_item = make_item(id=1, name="хлеб", quantity=None)

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group",
                    return_value=existing_item,
                ):
                    with patch(
                        "handlers.update_item_quantity", return_value=True
                    ) as mock_update:
                        from handlers import cmd_add

                        mock_message.text = "/add хлеб"
                        await cmd_add(mock_message, mock_state)

                        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_different_groups_not_combined(
        self, mock_message, mock_state
    ):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group", return_value=None
                ):
                    with patch(
                        "handlers.add_item", AsyncMock(return_value=1)
                    ) as mock_add:
                        from handlers import cmd_add

                        mock_message.text = "/add сыр 1кг"
                        await cmd_add(mock_message, mock_state)

                        mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_case_insensitive_cyrillic(self, mock_message, mock_state):
        mock_db = AsyncMock()
        existing_item = make_item(id=1, name="Сыр", quantity="1кг")

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group",
                    return_value=existing_item,
                ):
                    with patch(
                        "handlers.update_item_quantity", return_value=True
                    ) as mock_update:
                        from handlers import cmd_add

                        mock_message.text = "/add сыр 200г"
                        await cmd_add(mock_message, mock_state)

                        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_combine_grams_under_1000(self, mock_message, mock_state):
        mock_db = AsyncMock()
        existing_item = make_item(id=1, name="сыр", quantity="200г")

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.find_pending_item_in_unit_group",
                    return_value=existing_item,
                ):
                    with patch(
                        "handlers.update_item_quantity", return_value=True
                    ) as mock_update:
                        from handlers import cmd_add

                        mock_message.text = "/add сыр 300г"
                        await cmd_add(mock_message, mock_state)

                        mock_update.assert_called_once()


class TestEditProduct:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        message.reply_to_message = None
        message.edit_text = AsyncMock()
        message.bot = AsyncMock()
        return message

    @pytest.fixture
    def mock_callback(self):
        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123456
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.data = ""
        callback.answer = AsyncMock()
        callback.message = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.message.from_user = MagicMock()
        callback.message.from_user.id = 123456
        callback.message.from_user.username = "test_user"
        callback.message.from_user.full_name = "Test User"
        callback.message.text = ""
        callback.bot = AsyncMock()
        return callback

    @pytest.mark.asyncio
    async def test_callback_edit(self, mock_callback):
        mock_db = AsyncMock()
        item = make_item(id=1, name="молоко", quantity="2л")

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_item_by_id", return_value=item):
                    from handlers import callback_edit

                    mock_callback.data = "edit_1"
                    await callback_edit(mock_callback, AsyncMock())

                    mock_callback.message.answer.assert_called_once()
                    call_args = mock_callback.message.answer.call_args[0][0]
                    assert "Редактирование" in call_args

    @pytest.mark.asyncio
    async def test_callback_edit_unauthorized(self, mock_callback):
        with patch("handlers.check_access", return_value=False):
            from handlers import callback_edit

            mock_callback.data = "edit_1"
            await callback_edit(mock_callback, AsyncMock())

            mock_callback.answer.assert_called_once()
            assert "запрещён" in mock_callback.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_callback_edit_not_found(self, mock_callback):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_item_by_id", return_value=None):
                    from handlers import callback_edit

                    mock_callback.data = "edit_999"
                    await callback_edit(mock_callback, AsyncMock())

                    mock_callback.answer.assert_called_once()
                    assert "не найден" in mock_callback.answer.call_args[0][0]


class TestTemplates:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        message.reply_to_message = None
        message.edit_text = AsyncMock()
        message.bot = AsyncMock()
        return message

    @pytest.fixture
    def mock_callback(self):
        callback = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123456
        callback.from_user.username = "test_user"
        callback.from_user.full_name = "Test User"
        callback.data = ""
        callback.answer = AsyncMock()
        callback.message = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.message.from_user = MagicMock()
        callback.message.from_user.id = 123456
        callback.message.from_user.username = "test_user"
        callback.message.from_user.full_name = "Test User"
        callback.message.text = ""
        callback.bot = AsyncMock()
        return callback

    @pytest.fixture
    def mock_state(self):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        return state

    @pytest.mark.asyncio
    async def test_btn_templates_empty(self, mock_message, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_templates", return_value=[]):
                    from handlers import btn_templates

                    await btn_templates(mock_message, mock_state)

                    assert mock_message.answer.call_count >= 1
                    call_args = mock_message.answer.call_args_list[0][0][0]
                    assert "Шаблоны пусты" in call_args

    @pytest.mark.asyncio
    async def test_btn_templates_with_templates(self, mock_message, mock_state):
        mock_db = AsyncMock()
        templates = [
            make_template(id=1, name="Недельный", item_count=5),
            make_template(id=2, name="Праздник", item_count=10),
        ]

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_templates", return_value=templates):
                    from handlers import btn_templates

                    await btn_templates(mock_message, mock_state)

                    assert mock_message.answer.call_count >= 1
                    call_args = mock_message.answer.call_args_list[0][0][0]
                    assert "Недельный" in call_args
                    assert "Праздник" in call_args

    @pytest.mark.asyncio
    async def test_btn_templates_unauthorized(self, mock_message, mock_state):
        with patch("handlers.check_access", return_value=False):
            from handlers import btn_templates

            await btn_templates(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            assert "запрещён" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_callback_view_template(self, mock_callback, mock_state):
        mock_db = AsyncMock()
        template = make_template(id=1, name="Тестовый")
        items = [
            make_template_item(
                id=1, template_id=1, name="молоко", quantity="2л", category="dairy"
            ),
            make_template_item(
                id=2, template_id=1, name="хлеб", quantity=None, category="bakery"
            ),
        ]

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_template_by_id", return_value=template):
                    with patch(
                        "handlers.get_template_items_ordered", return_value=items
                    ):
                        from handlers import callback_view_template

                        mock_callback.data = "view_template_1"
                        await callback_view_template(mock_callback, mock_state)

                        mock_callback.message.edit_text.assert_called_once()
                        call_args = mock_callback.message.edit_text.call_args[0][0]
                        assert "Тестовый" in call_args
                        assert "молоко" in call_args

    @pytest.mark.asyncio
    async def test_btn_template_delete(self, mock_message, mock_state):
        mock_db = AsyncMock()
        template = make_template(id=1, name="Для удаления")
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_template_by_id", return_value=template):
                    from handlers import btn_template_delete

                    await btn_template_delete(mock_message, mock_state)

                    mock_message.answer.assert_called()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Удалить" in call_args

    @pytest.mark.asyncio
    async def test_callback_confirm_delete_template(self, mock_callback, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.delete_template", return_value=True):
                    with patch("handlers.get_all_templates", return_value=[]):
                        with patch(
                            "handlers.build_templates_message",
                            return_value=("text", None),
                        ):
                            from handlers import callback_confirm_delete_template

                            mock_callback.data = "confirm_del_template_1"
                            await callback_confirm_delete_template(
                                mock_callback, mock_state
                            )

                            mock_callback.message.edit_text.assert_called()

    @pytest.mark.asyncio
    async def test_btn_template_add_to_list_empty(self, mock_message, mock_state):
        mock_db = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch(
                    "handlers.get_template_by_id",
                    return_value={"id": 1, "name": "Тест"},
                ):
                    with patch("handlers.get_template_items", return_value=[]):
                        from handlers import btn_template_add_to_list

                        await btn_template_add_to_list(mock_message, mock_state)

                        mock_message.answer.assert_called()
                        call_args = mock_message.answer.call_args[0][0]
                        assert "пуст" in call_args.lower()

    @pytest.mark.asyncio
    async def test_btn_template_add_to_list_no_conflicts(
        self, mock_message, mock_state
    ):
        mock_db = AsyncMock()
        template = {"id": 1, "name": "Тестовый"}
        template_items = [make_item(id=1, name="молоко", quantity="2л")]
        list_items = [make_item(id=1, name="хлеб", quantity=None)]
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_template_by_id", return_value=template):
                    with patch(
                        "handlers.get_template_items", return_value=template_items
                    ):
                        with patch(
                            "handlers.get_pending_items", return_value=list_items
                        ):
                            with patch("handlers.add_item", AsyncMock(return_value=1)):
                                from handlers import btn_template_add_to_list

                                await btn_template_add_to_list(mock_message, mock_state)

                                mock_message.answer.assert_called()
                                call_args = mock_message.answer.call_args[0][0]
                                assert "Добавлено" in call_args

    @pytest.mark.asyncio
    async def test_btn_template_add_to_list_with_conflicts(
        self, mock_message, mock_state
    ):
        mock_db = AsyncMock()
        template = {"id": 1, "name": "Тестовый"}
        template_items = [make_item(id=1, name="молоко", quantity="2л")]
        list_items = [make_item(id=1, name="молоко", quantity="1л")]
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_template_by_id", return_value=template):
                    with patch(
                        "handlers.get_template_items", return_value=template_items
                    ):
                        with patch(
                            "handlers.get_pending_items", return_value=list_items
                        ):
                            from handlers import btn_template_add_to_list

                            await btn_template_add_to_list(mock_message, mock_state)

                            mock_message.answer.assert_called()
                            call_args = mock_message.answer.call_args[0][0]
                            assert "конфликтов" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_replace_all_conflicts(self, mock_callback, mock_state):
        mock_db = AsyncMock()
        mock_state.get_data = AsyncMock(
            return_value={
                "conflicts": [
                    {
                        "template_item": make_item(id=1, name="молоко", quantity="2л"),
                        "list_item": make_item(id=1, name="молоко", quantity="1л"),
                    }
                ],
                "non_conflicts": [],
                "user_display": "@test",
            }
        )

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.update_item_quantity", return_value=True):
                    with patch("handlers.add_item", AsyncMock(return_value=1)):
                        from handlers import callback_replace_all_conflicts

                        mock_callback.data = "replace_all_1"
                        await callback_replace_all_conflicts(mock_callback, mock_state)

                        mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_keep_all_conflicts(self, mock_callback, mock_state):
        mock_db = AsyncMock()
        mock_state.get_data = AsyncMock(
            return_value={
                "conflicts": [
                    {
                        "template_item": make_item(id=1, name="молоко", quantity="2л"),
                        "list_item": make_item(id=1, name="молоко", quantity="1л"),
                    }
                ],
                "non_conflicts": [],
                "user_display": "@test",
            }
        )

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.add_item", AsyncMock(return_value=1)):
                    from handlers import callback_keep_all_conflicts

                    mock_callback.data = "keep_all_1"
                    await callback_keep_all_conflicts(mock_callback, mock_state)

                    mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_btn_template_rename(self, mock_message, mock_state):
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            from handlers import btn_template_rename

            await btn_template_rename(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "название" in call_args.lower()

    @pytest.mark.asyncio
    async def test_btn_template_add_item(self, mock_message, mock_state):
        mock_state.get_data = AsyncMock(return_value={"current_template_id": 1})

        with patch("handlers.check_access", return_value=True):
            from handlers import btn_template_add_item

            await btn_template_add_item(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "название" in call_args.lower()

    @pytest.mark.asyncio
    async def test_callback_back_to_templates(self, mock_callback, mock_state):
        mock_db = AsyncMock()

        with patch("handlers.check_access", return_value=True):
            with patch(
                "handlers.get_db", return_value=make_async_context_manager(mock_db)
            ):
                with patch("handlers.get_all_templates", return_value=[]):
                    from handlers import callback_back_to_templates

                    mock_callback.data = "back_to_templates"
                    await callback_back_to_templates(mock_callback, mock_state)

                    mock_callback.message.edit_text.assert_called()


class TestTemplateFSM:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = "Название шаблона"
        message.answer = AsyncMock()
        return message

    @pytest.mark.asyncio
    async def test_process_template_name(self, mock_message):
        mock_db = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_template_by_id", return_value=None):
                with patch("handlers.create_template", AsyncMock(return_value=1)):
                    from handlers import process_template_name

                    await process_template_name(mock_message, state)

                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "создан" in call_args.lower()

    @pytest.mark.asyncio
    async def test_process_template_name_empty(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={})

        mock_message.text = "   "
        from handlers import process_template_name

        await process_template_name(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "пустым" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_cancel_template_name(self, mock_message):
        state = AsyncMock()
        state.clear = AsyncMock()

        from handlers import cancel_template_name

        mock_message.text = "❌ Отмена"
        await cancel_template_name(mock_message, state)

        state.clear.assert_called_once()
        assert "отменено" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_process_template_product_name(self, mock_message):
        state = AsyncMock()
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        mock_message.text = "молоко"
        from handlers import process_template_product_name

        await process_template_product_name(mock_message, state)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "единицу" in call_args.lower()

    @pytest.mark.asyncio
    async def test_finish_template_products(self, mock_message):
        state = AsyncMock()
        state.clear = AsyncMock()

        from handlers import finish_template_products

        mock_message.text = "✅ Готово"
        await finish_template_products(mock_message, state)

        state.clear.assert_called_once()
        assert "сохранён" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_process_template_product_amount(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"template_product_unit": "л"})
        state.set_state = AsyncMock()

        mock_message.text = "2"
        with patch("handlers.save_template_product", AsyncMock()):
            from handlers import process_template_product_amount

            await process_template_product_amount(mock_message, state)

    @pytest.mark.asyncio
    async def test_process_template_product_amount_invalid(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"template_product_unit": "л"})

        mock_message.text = "abc"
        from handlers import process_template_product_amount

        await process_template_product_amount(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "число" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_skip_template_product_unit(self, mock_message):
        state = AsyncMock()

        with patch("handlers.save_template_product", AsyncMock()):
            from handlers import skip_template_product_unit

            await skip_template_product_unit(mock_message, state)

    @pytest.mark.asyncio
    async def test_process_rename_template(self, mock_message):
        mock_db = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"rename_template_id": 1})
        state.clear = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.rename_template", return_value=True):
                with patch(
                    "handlers.build_template_detail_message",
                    return_value=("text", None),
                ):
                    from handlers import process_rename_template

                    mock_message.text = "Новое название"
                    await process_rename_template(mock_message, state)

                    mock_message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_rename_template(self, mock_message):
        state = AsyncMock()
        state.clear = AsyncMock()

        from handlers import cancel_rename_template

        mock_message.text = "❌ Отмена"
        await cancel_rename_template(mock_message, state)

        state.clear.assert_called_once()
        assert "отменено" in mock_message.answer.call_args[0][0].lower()


class TestEditProductFSM:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        return message

    @pytest.mark.asyncio
    async def test_edit_process_unit(self, mock_message):
        state = AsyncMock()
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        mock_message.text = "кг"
        from handlers import edit_process_unit

        await edit_process_unit(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "количество" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_process_unit_invalid(self, mock_message):
        state = AsyncMock()

        mock_message.text = "invalid"
        from handlers import edit_process_unit

        await edit_process_unit(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "выберите" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_skip_unit(self, mock_message):
        state = AsyncMock()

        with patch("handlers.save_edited_product", AsyncMock()):
            from handlers import edit_skip_unit

            await edit_skip_unit(mock_message, state)

    @pytest.mark.asyncio
    async def test_edit_process_amount(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"edit_unit": "кг"})

        with patch("handlers.save_edited_product", AsyncMock()):
            from handlers import edit_process_amount

            mock_message.text = "2"
            await edit_process_amount(mock_message, state)

    @pytest.mark.asyncio
    async def test_edit_process_amount_invalid(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"edit_unit": "кг"})

        mock_message.text = "abc"
        from handlers import edit_process_amount

        await edit_process_amount(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "число" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_process_amount_negative(self, mock_message):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"edit_unit": "кг"})

        mock_message.text = "-5"
        from handlers import edit_process_amount

        await edit_process_amount(mock_message, state)

        mock_message.answer.assert_called_once()
        assert "нуля" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_cancel_edit_unit(self, mock_message):
        state = AsyncMock()
        state.clear = AsyncMock()

        from handlers import cancel_edit_unit

        mock_message.text = "❌ Отмена"
        await cancel_edit_unit(mock_message, state)

        state.clear.assert_called_once()
        assert "отменено" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_cancel_edit_amount(self, mock_message):
        state = AsyncMock()
        state.clear = AsyncMock()

        from handlers import cancel_edit_amount

        mock_message.text = "❌ Отмена"
        await cancel_edit_amount(mock_message, state)

        state.clear.assert_called_once()
        assert "отменено" in mock_message.answer.call_args[0][0].lower()


class TestSaveProduct:
    @pytest.fixture
    def mock_message(self):
        message = AsyncMock()
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "test_user"
        message.from_user.full_name = "Test User"
        message.text = ""
        message.answer = AsyncMock()
        return message

    @pytest.mark.asyncio
    async def test_save_edited_product(self, mock_message):
        mock_db = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"edit_item_id": 1})
        state.clear = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.update_item_quantity", return_value=True):
                from handlers import save_edited_product

                await save_edited_product(mock_message, state, 2, "кг")

                state.clear.assert_called_once()
                assert "обновлено" in mock_message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_save_template_product(self, mock_message):
        mock_db = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(
            return_value={"template_id": 1, "template_product_name": "молоко"}
        )
        state.set_state = AsyncMock()

        with patch("handlers.get_db", return_value=make_async_context_manager(mock_db)):
            with patch("handlers.get_all_product_categories", return_value={}):
                with patch("handlers.categorize_product", return_value="dairy"):
                    with patch(
                        "handlers.add_item_to_template", AsyncMock(return_value=1)
                    ):
                        from handlers import save_template_product

                        await save_template_product(mock_message, state, 2, "л")

                        assert mock_message.answer.call_count >= 1
                        first_call = mock_message.answer.call_args_list[0][0][0]
                        assert "Добавлено" in first_call


class TestBuildTemplates:
    @pytest.mark.asyncio
    async def test_build_templates_message_empty(self):
        mock_db = AsyncMock()

        with patch("handlers.get_all_templates", return_value=[]):
            from handlers import build_templates_message

            text, keyboard = await build_templates_message(mock_db)

            assert "Шаблоны пусты" in text
            assert keyboard is not None

    @pytest.mark.asyncio
    async def test_build_templates_message_with_templates(self):
        mock_db = AsyncMock()
        templates = [
            make_template(id=1, name="Тестовый", item_count=3),
        ]

        with patch("handlers.get_all_templates", return_value=templates):
            from handlers import build_templates_message

            text, keyboard = await build_templates_message(mock_db)

            assert "Тестовый" in text
            assert keyboard is not None

    @pytest.mark.asyncio
    async def test_build_template_detail_message(self):
        mock_db = AsyncMock()
        template = make_template(id=1, name="Тестовый")
        items = [
            make_template_item(
                id=1, template_id=1, name="молоко", quantity="2л", category="dairy"
            ),
        ]

        with patch("handlers.get_template_by_id", return_value=template):
            with patch("handlers.get_template_items_ordered", return_value=items):
                from handlers import build_template_detail_message

                text, keyboard = await build_template_detail_message(mock_db, 1)

                assert "Тестовый" in text
                assert "молоко" in text
                assert keyboard is not None

    @pytest.mark.asyncio
    async def test_build_template_detail_message_not_found(self):
        mock_db = AsyncMock()

        with patch("handlers.get_template_by_id", return_value=None):
            from handlers import build_template_detail_message

            text, keyboard = await build_template_detail_message(mock_db, 999)

            assert "не найден" in text
            assert keyboard is None
