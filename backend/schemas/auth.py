from pydantic import BaseModel
from typing import List
import uuid


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    message: str = "ok"
    redirect: str | None = None


class VerifyTokenResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    role: str
    apps: List[str]
