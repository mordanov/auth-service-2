from pydantic import BaseModel
import uuid
from datetime import datetime


class TokenCreate(BaseModel):
    token_value: str
    user_id: uuid.UUID
    expires_at: datetime
