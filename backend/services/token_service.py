import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from models.token import AuthToken
from models.user import User
from repositories.token_repository import TokenRepository
from repositories.user_repository import UserRepository
from config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TokenService:
    @staticmethod
    async def generate_token(user_id, db: AsyncSession) -> str:
        token_value = secrets.token_hex(32)
        expires_at = _now() + timedelta(hours=settings.TOKEN_TTL_HOURS)
        repo = TokenRepository(db)
        token = AuthToken(
            token_value=token_value,
            user_id=user_id,
            expires_at=expires_at,
        )
        await repo.create(token)
        return token_value

    @staticmethod
    async def validate_token(token_value: str, db: AsyncSession) -> User | None:
        token_repo = TokenRepository(db)
        user_repo = UserRepository(db)

        token = await token_repo.get_by_value(token_value)
        if token is None:
            return None
        if token.expires_at <= _now():
            await token_repo.delete(token)
            return None

        user = await user_repo.get_by_id(token.user_id)
        if user is None or not user.is_active:
            return None

        token.last_used_at = _now()
        await db.flush()
        return user

    @staticmethod
    async def cleanup_expired(db: AsyncSession) -> None:
        repo = TokenRepository(db)
        await repo.delete_expired(_now())
        await db.commit()
