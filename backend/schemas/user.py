from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPatch(BaseModel):
    is_active: bool


class UserPatchResponse(BaseModel):
    id: uuid.UUID
    username: str
    is_active: bool

    model_config = {"from_attributes": True}


class AppAccessItem(BaseModel):
    app_name: str
    is_enabled: bool

    model_config = {"from_attributes": True}


class AppAccessListRequest(BaseModel):
    apps: List[AppAccessItem]
