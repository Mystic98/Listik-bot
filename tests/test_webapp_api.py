from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

import webapp.app as webapp_app
from database import add_user, create_room
from webapp.auth import TelegramIdentity
from webapp.schemas import CreateItemRequest, UpdateCategoryRequest, UpdateItemRequest


@pytest.fixture
def identity():
    return TelegramIdentity(
        telegram_id=987654321,
        username="regular_user",
        full_name="Regular User",
    )


@pytest.fixture
async def app_context(db, identity, monkeypatch):
    await add_user(db, identity.telegram_id, identity.username, identity.full_name, 1)
    room = await create_room(db, "Дом", identity.telegram_id)
    assert room is not None

    @asynccontextmanager
    async def fake_get_db():
        yield db

    monkeypatch.setattr(webapp_app, "get_db", fake_get_db)
    return room


@pytest.mark.asyncio
async def test_me_rooms_categories_and_items(app_context, identity):
    me = await webapp_app.get_me(identity)
    rooms = await webapp_app.get_rooms(identity)
    categories = await webapp_app.get_categories(identity)
    items = await webapp_app.get_items(app_context.id, identity)
    active_rooms = await webapp_app.activate_user_room(app_context.id, identity)

    assert me.status == "approved"
    assert rooms.active_room_id == app_context.id
    assert any(category["id"] == "other" for category in categories)
    assert items.items == []
    assert active_rooms.active_room_id == app_context.id


@pytest.mark.asyncio
async def test_item_lifecycle_and_stale_edit_conflict(app_context, identity):
    created = await webapp_app.create_item(
        app_context.id,
        CreateItemRequest(name="молоко", quantity="2л"),
        identity,
    )
    assert created.item.category == "dairy"
    assert created.item.version == 1

    updated = await webapp_app.update_item(
        app_context.id,
        created.item.id,
        UpdateItemRequest(
            name="молоко домашнее",
            quantity="3л",
            category="dairy",
            version=created.item.version,
        ),
        identity,
    )
    assert updated.item.version == 2

    with pytest.raises(HTTPException) as conflict:
        await webapp_app.update_item(
            app_context.id,
            created.item.id,
            UpdateItemRequest(
                name="старое значение",
                quantity="1л",
                category="dairy",
                version=created.item.version,
            ),
            identity,
        )
    assert conflict.value.status_code == 409

    purchased = await webapp_app.purchase_item(app_context.id, created.item.id, identity)
    assert purchased.item.is_purchased is True
    restored = await webapp_app.unpurchase_item(app_context.id, created.item.id, identity)
    assert restored.item.is_purchased is False

    categorized = await webapp_app.update_category(
        app_context.id,
        created.item.id,
        UpdateCategoryRequest(category="grocery"),
        identity,
    )
    assert categorized.item.category == "grocery"

    deleted = await webapp_app.delete_item(app_context.id, created.item.id, identity)
    assert deleted is None


@pytest.mark.asyncio
async def test_clear_purchased_is_room_scoped(app_context, identity):
    created = await webapp_app.create_item(
        app_context.id,
        CreateItemRequest(name="хлеб"),
        identity,
    )
    await webapp_app.purchase_item(app_context.id, created.item.id, identity)

    result = await webapp_app.clear_purchased(app_context.id, identity)

    assert result.items == []
