import asyncio
from sqlalchemy import select

from db.database import AsyncSessionLocal, engine
from db.database import Base
from models.user import User, UserAppAccess, PROTECTED_APPS
from config import settings
from services.pwd import hash_password


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            print("Seed: users table already has data, skipping.")
            return

        users_to_seed = []

        if settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
            users_to_seed.append(
                User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                )
            )

        if settings.USER1_USERNAME and settings.USER1_PASSWORD:
            users_to_seed.append(
                User(
                    username=settings.USER1_USERNAME,
                    password_hash=hash_password(settings.USER1_PASSWORD),
                    role="user",
                    is_active=True,
                )
            )

        if settings.USER2_USERNAME and settings.USER2_PASSWORD:
            users_to_seed.append(
                User(
                    username=settings.USER2_USERNAME,
                    password_hash=hash_password(settings.USER2_PASSWORD),
                    role="user",
                    is_active=True,
                )
            )

        for user in users_to_seed:
            db.add(user)

        await db.flush()

        for user in users_to_seed:
            for app_name in PROTECTED_APPS:
                db.add(
                    UserAppAccess(user_id=user.id, app_name=app_name, is_enabled=False)
                )

        await db.commit()
        print(f"Seed: created {len(users_to_seed)} user(s).")


if __name__ == "__main__":
    asyncio.run(seed())
