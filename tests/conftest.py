import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator

# Provide minimal env vars required by Settings before any backend module loads.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from main import app
from models.user import User, UserAppAccess, PROTECTED_APPS
from models.token import AuthToken
from models.log import AuthLog


# ── In-memory SQLite engine for tests ───────────────────────────────────────

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Patch cookie settings so httpx test client can receive/send cookies.
    # Tests run against http://test — Secure+domain restrictions break cookie flow.
    import config as cfg
    original_domain = cfg.settings.COOKIE_DOMAIN
    original_env = cfg.settings.ENVIRONMENT
    cfg.settings.COOKIE_DOMAIN = ""
    cfg.settings.ENVIRONMENT = "test"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    cfg.settings.COOKIE_DOMAIN = original_domain
    cfg.settings.ENVIRONMENT = original_env
    app.dependency_overrides.clear()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def make_user(
    db: AsyncSession,
    username: str = "testuser",
    password_hash: str | None = None,
    role: str = "user",
    is_active: bool = True,
    email: str | None = None,
) -> User:
    from passlib.context import CryptContext
    if password_hash is None:
        password_hash = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto").hash("password")
    user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def make_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_value: str | None = None,
    hours: float = 24,
) -> AuthToken:
    import secrets
    token = AuthToken(
        token_value=token_value or secrets.token_hex(32),
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=hours),
    )
    db.add(token)
    await db.flush()
    await db.refresh(token)
    return token


async def make_app_access(
    db: AsyncSession,
    user_id: uuid.UUID,
    enabled_apps: list[str] | None = None,
) -> None:
    enabled_apps = enabled_apps or []
    for app_name in PROTECTED_APPS:
        db.add(UserAppAccess(
            user_id=user_id,
            app_name=app_name,
            is_enabled=app_name in enabled_apps,
        ))
    await db.flush()
