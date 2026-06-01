from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserAppAccess, PROTECTED_APPS
from repositories.user_repository import UserRepository
from repositories.token_repository import TokenRepository
from schemas.user import UserCreate, AppAccessItem


_pwd_ctx = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


class UserService:
    @staticmethod
    async def create_user(data: UserCreate, db: AsyncSession) -> User:
        user_repo = UserRepository(db)

        existing_username = await user_repo.get_by_username(data.username)
        if existing_username:
            raise ValueError("username already exists")

        if data.email:
            existing_email = await user_repo.get_by_email(data.email)
            if existing_email:
                raise ValueError("email already exists")

        password_hash = _pwd_ctx.hash(data.password)
        user = User(
            username=data.username,
            email=data.email if data.email else None,
            password_hash=password_hash,
            role=data.role,
            is_active=True,
        )
        user = await user_repo.create(user)

        for app_name in PROTECTED_APPS:
            db.add(UserAppAccess(user_id=user.id, app_name=app_name, is_enabled=False))
        await db.flush()
        await db.commit()
        return user

    @staticmethod
    async def block_user(user_id, db: AsyncSession) -> User:
        user_repo = UserRepository(db)
        token_repo = TokenRepository(db)

        user = await user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("user_not_found")

        await token_repo.delete_by_user_id(user_id)
        user = await user_repo.update_active_status(user, False)
        await db.commit()
        return user

    @staticmethod
    async def unblock_user(user_id, db: AsyncSession) -> User:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("user_not_found")
        user = await user_repo.update_active_status(user, True)
        await db.commit()
        return user

    @staticmethod
    async def update_app_access(
        user_id,
        app_list: list[AppAccessItem],
        db: AsyncSession,
    ) -> list[UserAppAccess]:
        from sqlalchemy import select
        from models.user import UserAppAccess as UAA

        existing = await db.execute(
            select(UAA).where(UAA.user_id == user_id)
        )
        rows = {row.app_name: row for row in existing.scalars().all()}

        for item in app_list:
            if item.app_name in rows:
                rows[item.app_name].is_enabled = item.is_enabled
            else:
                db.add(UAA(user_id=user_id, app_name=item.app_name, is_enabled=item.is_enabled))

        await db.flush()
        await db.commit()

        result = await db.execute(
            select(UAA).where(UAA.user_id == user_id).order_by(UAA.app_name)
        )
        return list(result.scalars().all())
