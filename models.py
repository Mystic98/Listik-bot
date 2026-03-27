from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class User(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    full_name: str
    added_by: Optional[int] = None
    is_approved: bool = False
    created_at: Optional[datetime] = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("full_name cannot be empty")
        return v.strip()


class Item(BaseModel):
    id: int
    name: str
    quantity: Optional[str] = None
    added_by: int
    added_by_name: Optional[str] = None
    is_purchased: bool = False
    purchased_by: Optional[int] = None
    purchased_by_name: Optional[str] = None
    category: str = "other"
    created_at: Optional[datetime] = None
    purchased_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class Template(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class TemplateWithCount(Template):
    item_count: int = 0


class TemplateItem(BaseModel):
    id: int
    template_id: int
    name: str
    quantity: Optional[str] = None
    category: str = "other"
    created_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class Room(BaseModel):
    id: int
    name: str
    creator_id: int
    created_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class RoomMember(BaseModel):
    room_id: int
    telegram_id: int
    role: str = "member"
    joined_at: Optional[datetime] = None
