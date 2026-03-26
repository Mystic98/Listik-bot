import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    add_user,
    get_user_by_telegram_id,
    get_user_by_username,
    is_user_allowed,
    remove_user,
    get_all_users,
    get_approved_telegram_ids,
    add_item,
    get_all_items,
    get_pending_items,
    get_purchased_items,
    get_item_by_id,
    mark_as_purchased,
    unmark_purchased,
    remove_item,
    clear_purchased_items,
    find_pending_item_by_name,
    update_item_quantity,
    get_all_items_ordered,
    add_pending_user,
    approve_user,
    reject_user,
    get_pending_users,
    get_user_by_username_all,
    find_pending_item_by_name_and_unit,
    find_pending_item_in_unit_group,
    create_template,
    get_all_templates,
    get_template_by_id,
    get_template_by_name,
    delete_template,
    rename_template,
    add_item_to_template,
    get_template_items,
    get_template_item_by_id,
    remove_template_item,
    update_template_item,
    create_template_from_items,
)
from models import Item


class TestUsers:
    @pytest.mark.asyncio
    async def test_add_user(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])

        assert user is not None
        assert user.telegram_id == regular_user["telegram_id"]
        assert user.username == regular_user["username"]
        assert user.full_name == regular_user["full_name"]

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, db):
        user = await get_user_by_telegram_id(db, 999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        user = await get_user_by_username(db, regular_user["username"])

        assert user is not None
        assert user.telegram_id == regular_user["telegram_id"]

    @pytest.mark.asyncio
    async def test_get_user_by_username_with_at(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        user = await get_user_by_username(db, f"@{regular_user['username']}")

        assert user is not None

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, db):
        user = await get_user_by_username(db, "nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_is_user_allowed_true(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        allowed = await is_user_allowed(db, regular_user["telegram_id"])
        assert allowed is True

    @pytest.mark.asyncio
    async def test_is_user_allowed_false(self, db):
        allowed = await is_user_allowed(db, 999999)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_remove_user(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        success = await remove_user(db, regular_user["telegram_id"])
        assert success is True

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])
        assert user is None

    @pytest.mark.asyncio
    async def test_remove_user_not_found(self, db):
        success = await remove_user(db, 999999)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_all_users(self, db, admin_user, regular_user):
        await add_user(
            db,
            admin_user["telegram_id"],
            admin_user["username"],
            admin_user["full_name"],
            123,
        )
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        users = await get_all_users(db)

        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_all_users_empty(self, db):
        users = await get_all_users(db)
        assert users == []

    @pytest.mark.asyncio
    async def test_add_user_replace_existing(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
        )

        await add_user(db, regular_user["telegram_id"], "new_username", "New Name", 456)

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])
        assert user.username == "new_username"
        assert user.full_name == "New Name"


class TestItems:
    @pytest.mark.asyncio
    async def test_add_item(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], regular_user["full_name"]
        )

        assert item_id is not None
        assert item_id > 0

    @pytest.mark.asyncio
    async def test_get_all_items(self, db, regular_user):
        await add_item(db, "молоко", "2л", regular_user["telegram_id"], "User")
        await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")

        items = await get_all_items(db)

        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_all_items_empty(self, db):
        items = await get_all_items(db)
        assert items == []

    @pytest.mark.asyncio
    async def test_get_pending_items(self, db, regular_user):
        await add_item(db, "молоко", "2л", regular_user["telegram_id"], "User")
        item_id = await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")

        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "User")

        items = await get_pending_items(db)

        assert len(items) == 1
        assert items[0].name == "молоко"

    @pytest.mark.asyncio
    async def test_get_purchased_items(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )
        await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")

        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "User")

        items = await get_purchased_items(db)

        assert len(items) == 1
        assert items[0].name == "молоко"

    @pytest.mark.asyncio
    async def test_get_item_by_id(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        item = await get_item_by_id(db, item_id)

        assert item is not None
        assert item.name == "молоко"
        assert item.quantity == "2л"

    @pytest.mark.asyncio
    async def test_get_item_by_id_not_found(self, db):
        item = await get_item_by_id(db, 999999)
        assert item is None

    @pytest.mark.asyncio
    async def test_mark_as_purchased(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        success = await mark_as_purchased(
            db, item_id, regular_user["telegram_id"], "Buyer"
        )

        assert success is True

        item = await get_item_by_id(db, item_id)
        assert item.is_purchased == 1
        assert item.purchased_by == regular_user["telegram_id"]

    @pytest.mark.asyncio
    async def test_mark_as_purchased_already_purchased(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "Buyer")
        success = await mark_as_purchased(db, item_id, 999, "Another")

        assert success is False

    @pytest.mark.asyncio
    async def test_mark_as_purchased_not_found(self, db):
        success = await mark_as_purchased(db, 999999, 123, "User")
        assert success is False

    @pytest.mark.asyncio
    async def test_unmark_purchased(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "Buyer")

        success = await unmark_purchased(db, item_id)

        assert success is True

        item = await get_item_by_id(db, item_id)
        assert item.is_purchased == 0

    @pytest.mark.asyncio
    async def test_unmark_purchased_not_purchased(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        success = await unmark_purchased(db, item_id)

        assert success is False

    @pytest.mark.asyncio
    async def test_remove_item(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        success = await remove_item(db, item_id)

        assert success is True

        item = await get_item_by_id(db, item_id)
        assert item is None

    @pytest.mark.asyncio
    async def test_remove_item_not_found(self, db):
        success = await remove_item(db, 999999)
        assert success is False

    @pytest.mark.asyncio
    async def test_clear_purchased_items(self, db, regular_user):
        item1 = await add_item(db, "молоко", "2л", regular_user["telegram_id"], "User")
        item2 = await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")
        await add_item(db, "яйца", "10 шт", regular_user["telegram_id"], "User")

        await mark_as_purchased(db, item1, regular_user["telegram_id"], "User")
        await mark_as_purchased(db, item2, regular_user["telegram_id"], "User")

        count = await clear_purchased_items(db)

        assert count == 2

        items = await get_all_items(db)
        assert len(items) == 1
        assert items[0].name == "яйца"

    @pytest.mark.asyncio
    async def test_clear_purchased_items_empty(self, db):
        count = await clear_purchased_items(db)
        assert count == 0

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_without_quantity(self, db, regular_user):
        await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")

        item = await find_pending_item_by_name(db, "хлеб", None)

        assert item is not None
        assert item.name == "хлеб"
        assert item.quantity is None

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_not_found(self, db):
        item = await find_pending_item_by_name(db, "молоко", None)
        assert item is None

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_and_unit_found(self, db, regular_user):
        await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_by_name_and_unit(db, "сыр", "кг")

        assert item is not None
        assert item.name == "сыр"
        assert item.quantity == "1кг"

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_and_unit_not_found(self, db):
        item = await find_pending_item_by_name_and_unit(db, "сыр", "кг")
        assert item is None

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_and_unit_different_unit(
        self, db, regular_user
    ):
        await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_by_name_and_unit(db, "сыр", "г")

        assert item is None

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_and_unit_case_insensitive(
        self, db, regular_user
    ):
        await add_item(db, "Сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_by_name_and_unit(db, "сыр", "кг")

        assert item is not None

    @pytest.mark.asyncio
    async def test_find_pending_item_by_name_and_unit_purchased(self, db, regular_user):
        item_id = await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")
        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "Buyer")

        item = await find_pending_item_by_name_and_unit(db, "сыр", "кг")

        assert item is None
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )
        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "Buyer")

        item = await find_pending_item_by_name(db, "молоко", "2л")

        assert item is None

    @pytest.mark.asyncio
    async def test_update_item_quantity(self, db, regular_user):
        item_id = await add_item(
            db, "молоко", "2л", regular_user["telegram_id"], "User"
        )

        success = await update_item_quantity(db, item_id, "5л")

        assert success is True

        item = await get_item_by_id(db, item_id)
        assert item.quantity == "5л"

    @pytest.mark.asyncio
    async def test_update_item_quantity_not_found(self, db):
        success = await update_item_quantity(db, 999999, "5л")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_all_items_ordered(self, db, regular_user):
        item1 = await add_item(db, "молоко", "2л", regular_user["telegram_id"], "User")
        item2 = await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")
        item3 = await add_item(db, "яйца", "10 шт", regular_user["telegram_id"], "User")

        await mark_as_purchased(db, item1, regular_user["telegram_id"], "Buyer")

        items = await get_all_items_ordered(db)

        assert len(items) == 3
        assert items[0].name == "хлеб"
        assert items[1].name == "яйца"
        assert items[2].name == "молоко"
        assert items[0].is_purchased == 0
        assert items[1].is_purchased == 0
        assert items[2].is_purchased == 1

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_weight_kg(self, db, regular_user):
        await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "сыр", "weight")

        assert item is not None
        assert item.name == "сыр"
        assert item.quantity == "1кг"

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_weight_grams(self, db, regular_user):
        await add_item(db, "сыр", "500г", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "сыр", "weight")

        assert item is not None
        assert item.name == "сыр"

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_volume(self, db, regular_user):
        await add_item(db, "молоко", "1л", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "молоко", "volume")

        assert item is not None
        assert item.name == "молоко"

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_pieces(self, db, regular_user):
        await add_item(db, "хлеб", "2шт", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "хлеб", "pieces")

        assert item is not None
        assert item.name == "хлеб"

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_without_unit(self, db, regular_user):
        await add_item(db, "хлеб", None, regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "хлеб", "pieces")

        assert item is not None
        assert item.name == "хлеб"
        assert item.quantity is None

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_not_found_different_group(
        self, db, regular_user
    ):
        await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "сыр", "volume")

        assert item is None

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_not_found_name(
        self, db, regular_user
    ):
        await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "молоко", "weight")

        assert item is None

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_case_insensitive(
        self, db, regular_user
    ):
        await add_item(db, "Сыр", "1кг", regular_user["telegram_id"], "User")

        item = await find_pending_item_in_unit_group(db, "сыр", "weight")

        assert item is not None

    @pytest.mark.asyncio
    async def test_find_pending_item_in_unit_group_purchased(self, db, regular_user):
        item_id = await add_item(db, "сыр", "1кг", regular_user["telegram_id"], "User")
        await mark_as_purchased(db, item_id, regular_user["telegram_id"], "Buyer")

        item = await find_pending_item_in_unit_group(db, "сыр", "weight")

        assert item is None


class TestPendingUsers:
    @pytest.mark.asyncio
    async def test_add_pending_user(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])

        assert user is not None
        assert user.is_approved == 0

    @pytest.mark.asyncio
    async def test_approve_user(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        success = await approve_user(db, regular_user["telegram_id"])

        assert success is True

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])
        assert user.is_approved == 1

    @pytest.mark.asyncio
    async def test_approve_user_not_found(self, db):
        success = await approve_user(db, 999999)
        assert success is False

    @pytest.mark.asyncio
    async def test_reject_user(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        success = await reject_user(db, regular_user["telegram_id"])

        assert success is True

        user = await get_user_by_telegram_id(db, regular_user["telegram_id"])
        assert user is None

    @pytest.mark.asyncio
    async def test_reject_user_not_pending(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
            approved=True,
        )

        success = await reject_user(db, regular_user["telegram_id"])

        assert success is False

    @pytest.mark.asyncio
    async def test_get_pending_users(self, db, regular_user, admin_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )
        await add_user(
            db,
            admin_user["telegram_id"],
            admin_user["username"],
            admin_user["full_name"],
            123,
            approved=True,
        )

        pending = await get_pending_users(db)

        assert len(pending) == 1
        assert pending[0].telegram_id == regular_user["telegram_id"]

    @pytest.mark.asyncio
    async def test_get_pending_users_empty(self, db):
        pending = await get_pending_users(db)
        assert pending == []

    @pytest.mark.asyncio
    async def test_get_approved_telegram_ids(self, db, regular_user, admin_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )
        await add_user(
            db,
            admin_user["telegram_id"],
            admin_user["username"],
            admin_user["full_name"],
            123,
            approved=True,
        )

        ids = await get_approved_telegram_ids(db)

        assert len(ids) == 1
        assert admin_user["telegram_id"] in ids
        assert regular_user["telegram_id"] not in ids

    @pytest.mark.asyncio
    async def test_get_approved_telegram_ids_empty(self, db):
        ids = await get_approved_telegram_ids(db)
        assert ids == []

    @pytest.mark.asyncio
    async def test_is_user_allowed_pending(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        allowed = await is_user_allowed(db, regular_user["telegram_id"])

        assert allowed is False

    @pytest.mark.asyncio
    async def test_is_user_allowed_approved(self, db, regular_user):
        await add_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
            123,
            approved=True,
        )

        allowed = await is_user_allowed(db, regular_user["telegram_id"])

        assert allowed is True

    @pytest.mark.asyncio
    async def test_get_user_by_username_all_pending(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        user = await get_user_by_username_all(db, regular_user["username"])

        assert user is not None
        assert user.is_approved == 0

    @pytest.mark.asyncio
    async def test_get_user_by_username_only_approved(self, db, regular_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )

        user = await get_user_by_username(db, regular_user["username"])

        assert user is None

    @pytest.mark.asyncio
    async def test_get_all_users_only_approved(self, db, regular_user, admin_user):
        await add_pending_user(
            db,
            regular_user["telegram_id"],
            regular_user["username"],
            regular_user["full_name"],
        )
        await add_user(
            db,
            admin_user["telegram_id"],
            admin_user["username"],
            admin_user["full_name"],
            123,
            approved=True,
        )

        users = await get_all_users(db)

        assert len(users) == 1
        assert users[0].telegram_id == admin_user["telegram_id"]


class TestTemplates:
    @pytest.mark.asyncio
    async def test_create_template(self, db):
        template_id = await create_template(db, "Недельный запас")
        assert template_id is not None
        assert template_id > 0

    @pytest.mark.asyncio
    async def test_get_all_templates_empty(self, db):
        templates = await get_all_templates(db)
        assert templates == []

    @pytest.mark.asyncio
    async def test_get_all_templates(self, db):
        await create_template(db, "Шаблон 1")
        await create_template(db, "Шаблон 2")

        templates = await get_all_templates(db)

        assert len(templates) == 2

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, db):
        template_id = await create_template(db, "Тестовый")

        template = await get_template_by_id(db, template_id)

        assert template is not None
        assert template.name == "Тестовый"

    @pytest.mark.asyncio
    async def test_get_template_by_id_not_found(self, db):
        template = await get_template_by_id(db, 999)
        assert template is None

    @pytest.mark.asyncio
    async def test_get_template_by_name(self, db):
        await create_template(db, "Название")

        template = await get_template_by_name(db, "Название")

        assert template is not None
        assert template.name == "Название"

    @pytest.mark.asyncio
    async def test_get_template_by_name_case_insensitive(self, db):
        await create_template(db, "Название")

        template = await get_template_by_name(db, "название")

        assert template is not None

    @pytest.mark.asyncio
    async def test_delete_template(self, db):
        template_id = await create_template(db, "Для удаления")

        success = await delete_template(db, template_id)

        assert success is True
        template = await get_template_by_id(db, template_id)
        assert template is None

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self, db):
        success = await delete_template(db, 999)
        assert success is False

    @pytest.mark.asyncio
    async def test_rename_template(self, db):
        template_id = await create_template(db, "Старое название")

        success = await rename_template(db, template_id, "Новое название")

        assert success is True
        template = await get_template_by_id(db, template_id)
        assert template.name == "Новое название"

    @pytest.mark.asyncio
    async def test_rename_template_duplicate(self, db):
        await create_template(db, "Шаблон 1")
        template_id2 = await create_template(db, "Шаблон 2")

        success = await rename_template(db, template_id2, "Шаблон 1")

        assert success is False


class TestTemplateItems:
    @pytest.mark.asyncio
    async def test_add_item_to_template(self, db):
        template_id = await create_template(db, "Тест")

        item_id = await add_item_to_template(db, template_id, "молоко", "2л")

        assert item_id is not None

    @pytest.mark.asyncio
    async def test_get_template_items(self, db):
        template_id = await create_template(db, "Тест")
        await add_item_to_template(db, template_id, "молоко", "2л")
        await add_item_to_template(db, template_id, "хлеб", None)

        items = await get_template_items(db, template_id)

        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_template_items_empty(self, db):
        template_id = await create_template(db, "Пустой")

        items = await get_template_items(db, template_id)

        assert items == []

    @pytest.mark.asyncio
    async def test_get_template_item_by_id(self, db):
        template_id = await create_template(db, "Тест")
        item_id = await add_item_to_template(db, template_id, "сыр", "500г")

        item = await get_template_item_by_id(db, item_id)

        assert item is not None
        assert item.name == "сыр"
        assert item.quantity == "500г"

    @pytest.mark.asyncio
    async def test_get_template_item_by_id_not_found(self, db):
        item = await get_template_item_by_id(db, 999)
        assert item is None

    @pytest.mark.asyncio
    async def test_remove_template_item(self, db):
        template_id = await create_template(db, "Тест")
        item_id = await add_item_to_template(db, template_id, "молоко", "1л")

        success = await remove_template_item(db, item_id)

        assert success is True
        item = await get_template_item_by_id(db, item_id)
        assert item is None

    @pytest.mark.asyncio
    async def test_remove_template_item_not_found(self, db):
        success = await remove_template_item(db, 999)
        assert success is False

    @pytest.mark.asyncio
    async def test_update_template_item(self, db):
        template_id = await create_template(db, "Тест")
        item_id = await add_item_to_template(db, template_id, "молоко", "1л")

        success = await update_template_item(db, item_id, "3л")

        assert success is True
        item = await get_template_item_by_id(db, item_id)
        assert item.quantity == "3л"

    @pytest.mark.asyncio
    async def test_update_template_item_not_found(self, db):
        success = await update_template_item(db, 999, "1л")
        assert success is False

    @pytest.mark.asyncio
    async def test_create_template_from_items(self, db):
        items = [
            Item(id=0, name="молоко", quantity="2л", added_by=1),
            Item(id=0, name="хлеб", quantity=None, added_by=1),
            Item(id=0, name="сыр", quantity="500г", added_by=1),
        ]

        template_id = await create_template_from_items(db, "Из списка", items)

        assert template_id is not None
        template_items = await get_template_items(db, template_id)
        assert len(template_items) == 3

    @pytest.mark.asyncio
    async def test_template_item_count(self, db):
        template_id = await create_template(db, "С товарами")
        await add_item_to_template(db, template_id, "товар 1", None)
        await add_item_to_template(db, template_id, "товар 2", "1кг")

        templates = await get_all_templates(db)

        assert len(templates) == 1
        assert templates[0].item_count == 2
