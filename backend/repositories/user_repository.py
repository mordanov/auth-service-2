from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User, UserAppAccess
import uuid


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_active_status(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list_all(self) -> list[User]:
        result = await self.db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def get_app_access(self, user_id: uuid.UUID) -> list[UserAppAccess]:
        result = await self.db.execute(
            select(UserAppAccess)
            .where(UserAppAccess.user_id == user_id)
            .order_by(UserAppAccess.app_name)
        )
        return list(result.scalars().all())
