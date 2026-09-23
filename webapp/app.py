from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles

from categories import categorize_product, get_all_categories
from config import settings
from database import (
    add_or_merge_item_in_room,
    clear_purchased_items,
    create_room,
    get_active_room,
    get_all_items_ordered,
    get_all_product_categories,
    get_db,
    get_item_by_id_in_room,
    get_room_by_id,
    get_user_by_telegram_id,
    get_user_rooms,
    is_room_member,
    mark_as_purchased_in_room,
    remove_item_in_room,
    unmark_purchased_in_room,
    set_active_room,
    update_item_in_room,
    update_item_category_in_room,
)
from models import Item
from webapp.auth import TelegramIdentity, TelegramInitDataError, validate_init_data
from webapp.realtime import realtime
from webapp.schemas import (
    CreateItemRequest,
    ItemMutationResponse,
    ItemResponse,
    ItemsResponse,
    MeResponse,
    RoomResponse,
    RoomsResponse,
    UpdateCategoryRequest,
    UpdateItemRequest,
    CreateRoomRequest,
)


app = FastAPI(title="Listik Mini App API", version="0.1.0")


def _item_response(item: Item) -> ItemResponse:
    return ItemResponse.model_validate(item.model_dump())


def _auth_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительные данные Telegram",
    )


def _get_init_data(
    authorization: Annotated[str | None, Header()] = None,
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> str:
    if x_telegram_init_data:
        return x_telegram_init_data
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ")
    raise _auth_error()


def get_identity(init_data: Annotated[str, Depends(_get_init_data)]) -> TelegramIdentity:
    try:
        return validate_init_data(
            init_data,
            settings.bot_token,
            settings.telegram_init_data_max_age,
        )
    except TelegramInitDataError as exc:
        raise _auth_error() from exc


Identity = Annotated[TelegramIdentity, Depends(get_identity)]


async def _get_user_status(identity: TelegramIdentity) -> tuple[str, bool]:
    async with get_db() as db:
        user = await get_user_by_telegram_id(db, identity.telegram_id)

    is_admin = identity.telegram_id == settings.admin_id
    if is_admin or (user and user.is_approved):
        return "approved", is_admin
    if user:
        return "pending", False
    return "not_registered", False


async def _require_room_member(identity: TelegramIdentity, room_id: int) -> None:
    status_name, _ = await _get_user_status(identity)
    if status_name != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ ещё не одобрен")

    async with get_db() as db:
        room = await get_room_by_id(db, room_id)
        is_member = room is not None and await is_room_member(
            db, room_id, identity.telegram_id
        )
    if not is_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/me", response_model=MeResponse)
async def get_me(identity: Identity) -> MeResponse:
    status_name, is_admin = await _get_user_status(identity)
    return MeResponse(
        telegram_id=identity.telegram_id,
        username=identity.username,
        full_name=identity.full_name,
        status=status_name,
        is_admin=is_admin,
    )


@app.get("/api/v1/rooms", response_model=RoomsResponse)
async def get_rooms(identity: Identity) -> RoomsResponse:
    status_name, _ = await _get_user_status(identity)
    if status_name != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ ещё не одобрен")

    async with get_db() as db:
        rooms = await get_user_rooms(db, identity.telegram_id)
        active_room = await get_active_room(db, identity.telegram_id)

    return RoomsResponse(
        active_room_id=active_room.id if active_room else None,
        rooms=[
            RoomResponse(
                id=room.id,
                name=room.name,
                creator_id=room.creator_id,
                is_creator=room.creator_id == identity.telegram_id,
                is_active=active_room is not None and room.id == active_room.id,
            )
            for room in rooms
        ],
    )


@app.post("/api/v1/rooms", response_model=RoomResponse)
async def create_user_room(payload: CreateRoomRequest, identity: Identity) -> RoomResponse:
    status_name, _ = await _get_user_status(identity)
    if status_name != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ ещё не одобрен")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Название комнаты не может быть пустым")
    async with get_db() as db:
        room = await create_room(db, name, identity.telegram_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="У пользователя уже есть созданная комната")
    return RoomResponse(
        id=room.id,
        name=room.name,
        creator_id=room.creator_id,
        is_creator=True,
        is_active=True,
    )


@app.post("/api/v1/rooms/{room_id}/activate", response_model=RoomsResponse)
async def activate_user_room(room_id: int, identity: Identity) -> RoomsResponse:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        await set_active_room(db, identity.telegram_id, room_id)
    return await get_rooms(identity)


@app.get("/api/v1/categories")
async def get_categories(identity: Identity) -> list[dict[str, str]]:
    status_name, _ = await _get_user_status(identity)
    if status_name != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ ещё не одобрен")
    return [
        {"id": category_id, "name": str(category["name"])}
        for category_id, category in get_all_categories().items()
    ]


@app.get("/api/v1/rooms/{room_id}/items", response_model=ItemsResponse)
async def get_items(room_id: int, identity: Identity) -> ItemsResponse:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        items = await get_all_items_ordered(db, room_id=room_id)
    return ItemsResponse(
        room_id=room_id,
        items=[_item_response(item) for item in items],
    )


@app.post("/api/v1/rooms/{room_id}/items", response_model=ItemMutationResponse)
async def create_item(
    room_id: int,
    payload: CreateItemRequest,
    identity: Identity,
) -> ItemMutationResponse:
    await _require_room_member(identity, room_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Название не может быть пустым")

    async with get_db() as db:
        user_categories = await get_all_product_categories(db)
        category = payload.category or categorize_product(name, user_categories)
        item_id, merged = await add_or_merge_item_in_room(
            db,
            name=name,
            quantity=payload.quantity,
            added_by=identity.telegram_id,
            added_by_name=identity.full_name,
            category=category,
            room_id=room_id,
        )
        item = await get_item_by_id_in_room(db, item_id, room_id)

    if item is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Товар не создан")
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item.id},
    )
    return ItemMutationResponse(
        item=_item_response(item),
        merged=merged,
        needs_category=payload.category is None and category == "other",
    )


@app.patch("/api/v1/rooms/{room_id}/items/{item_id}/category", response_model=ItemMutationResponse)
async def update_category(
    room_id: int,
    item_id: int,
    payload: UpdateCategoryRequest,
    identity: Identity,
) -> ItemMutationResponse:
    await _require_room_member(identity, room_id)
    if payload.category not in get_all_categories():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Неизвестная категория")

    async with get_db() as db:
        item = await get_item_by_id_in_room(db, item_id, room_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
        updated = await update_item_category_in_room(
            db, item_id, room_id, payload.category
        )
        item = await get_item_by_id_in_room(db, item_id, room_id)

    if not updated or item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Товар уже изменён")
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item.id},
    )
    return ItemMutationResponse(item=_item_response(item))


@app.patch("/api/v1/rooms/{room_id}/items/{item_id}", response_model=ItemMutationResponse)
async def update_item(
    room_id: int,
    item_id: int,
    payload: UpdateItemRequest,
    identity: Identity,
) -> ItemMutationResponse:
    await _require_room_member(identity, room_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Название не может быть пустым",
        )
    if payload.category not in get_all_categories():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Неизвестная категория",
        )

    async with get_db() as db:
        item = await get_item_by_id_in_room(db, item_id, room_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
        updated_item = await update_item_in_room(
            db,
            item_id,
            room_id,
            name,
            payload.quantity,
            payload.category,
            payload.version,
        )

    if updated_item is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Товар уже изменён другим участником",
        )
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item_id},
    )
    return ItemMutationResponse(item=_item_response(updated_item))


@app.delete("/api/v1/rooms/{room_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(room_id: int, item_id: int, identity: Identity) -> None:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        deleted = await remove_item_in_room(db, item_id, room_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item_id},
    )


@app.post("/api/v1/rooms/{room_id}/clear-purchased", response_model=ItemsResponse)
async def clear_purchased(room_id: int, identity: Identity) -> ItemsResponse:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        await clear_purchased_items(db, room_id=room_id)
        items = await get_all_items_ordered(db, room_id=room_id)
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "items", "entity_id": room_id},
    )
    return ItemsResponse(room_id=room_id, items=[_item_response(item) for item in items])


@app.post("/api/v1/rooms/{room_id}/items/{item_id}/purchase", response_model=ItemMutationResponse)
async def purchase_item(room_id: int, item_id: int, identity: Identity) -> ItemMutationResponse:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        item = await get_item_by_id_in_room(db, item_id, room_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
        updated = await mark_as_purchased_in_room(
            db, item_id, room_id, identity.telegram_id, identity.full_name
        )
        item = await get_item_by_id_in_room(db, item_id, room_id)

    if not updated or item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Товар уже изменён")
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item.id},
    )
    return ItemMutationResponse(item=_item_response(item))


@app.post("/api/v1/rooms/{room_id}/items/{item_id}/unpurchase", response_model=ItemMutationResponse)
async def unpurchase_item(room_id: int, item_id: int, identity: Identity) -> ItemMutationResponse:
    await _require_room_member(identity, room_id)
    async with get_db() as db:
        item = await get_item_by_id_in_room(db, item_id, room_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
        updated = await unmark_purchased_in_room(db, item_id, room_id)
        item = await get_item_by_id_in_room(db, item_id, room_id)

    if not updated or item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Товар уже изменён")
    await realtime.publish(
        room_id,
        {"type": "items.invalidated", "room_id": room_id, "entity": "item", "entity_id": item.id},
    )
    return ItemMutationResponse(item=_item_response(item))


@app.websocket("/ws/rooms/{room_id}")
async def room_websocket(websocket: WebSocket, room_id: int) -> None:
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        identity = validate_init_data(
            str(payload.get("init_data", "")),
            settings.bot_token,
            settings.telegram_init_data_max_age,
        )
        await _require_room_member(identity, room_id)
        await realtime.connect(room_id, websocket)
        await websocket.send_json({"type": "ready", "room_id": room_id})
        while True:
            await websocket.receive_text()
    except (TelegramInitDataError, HTTPException):
        await websocket.close(code=4401)
    except WebSocketDisconnect:
        pass
    finally:
        if "identity" in locals():
            await realtime.disconnect(room_id, websocket)


static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    async def frontend_not_built() -> dict[str, str]:
        return {"status": "ok", "message": "Mini App frontend is not built"}
