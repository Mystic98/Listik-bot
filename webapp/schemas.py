from datetime import datetime

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    telegram_id: int
    username: str | None = None
    full_name: str
    status: str
    is_admin: bool = False


class RoomResponse(BaseModel):
    id: int
    name: str
    creator_id: int
    is_creator: bool
    is_active: bool


class RoomsResponse(BaseModel):
    active_room_id: int | None
    rooms: list[RoomResponse]


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ItemResponse(BaseModel):
    id: int
    name: str
    quantity: str | None = None
    category: str
    is_purchased: bool
    added_by: int
    added_by_name: str | None = None
    purchased_by: int | None = None
    purchased_by_name: str | None = None
    created_at: datetime | None = None
    purchased_at: datetime | None = None
    version: int = 1


class ItemsResponse(BaseModel):
    room_id: int
    items: list[ItemResponse]


class CreateItemRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: str | None = Field(default=None, max_length=32)
    category: str | None = None


class ItemMutationResponse(BaseModel):
    item: ItemResponse
    merged: bool = False
    needs_category: bool = False


class UpdateCategoryRequest(BaseModel):
    category: str = Field(min_length=1, max_length=32)


class UpdateItemRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: str | None = Field(default=None, max_length=32)
    category: str = Field(min_length=1, max_length=32)
    version: int = Field(ge=1)
