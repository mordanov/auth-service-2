from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.token import AuthToken
from datetime import datetime
import uuid


class TokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, token: AuthToken) -> AuthToken:
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def get_by_value(self, token_value: str) -> AuthToken | None:
        result = await self.db.execute(
            select(AuthToken).where(AuthToken.token_value == token_value)
        )
        return result.scalar_one_or_none()

    async def delete(self, token: AuthToken) -> None:
        await self.db.delete(token)
        await self.db.flush()

    async def delete_by_user_id(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(AuthToken).where(AuthToken.user_id == user_id)
        )
        await self.db.flush()

    async def delete_expired(self, now: datetime) -> None:
        await self.db.execute(
            delete(AuthToken).where(AuthToken.expires_at <= now)
        )
        await self.db.flush()
