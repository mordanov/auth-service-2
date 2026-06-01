import uuid
import pytest

from tests.conftest import make_user, make_app_access
from repositories.user_repository import UserRepository
from models.user import PROTECTED_APPS


class TestUserRepository:
    async def test_get_by_username_hit(self, db):
        user = await make_user(db, username="alice")
        await db.commit()

        repo = UserRepository(db)
        result = await repo.get_by_username("alice")
        assert result is not None
        assert result.username == "alice"

    async def test_get_by_username_miss(self, db):
        repo = UserRepository(db)
        result = await repo.get_by_username("nobody")
        assert result is None

    async def test_get_by_email_hit(self, db):
        user = await make_user(db, username="bob", email="bob@example.com")
        await db.commit()

        repo = UserRepository(db)
        result = await repo.get_by_email("bob@example.com")
        assert result is not None
        assert result.email == "bob@example.com"

    async def test_get_by_email_miss(self, db):
        repo = UserRepository(db)
        result = await repo.get_by_email("missing@example.com")
        assert result is None

    async def test_create_persists_user(self, db):
        from models.user import User
        import uuid as _uuid

        repo = UserRepository(db)
        user = User(
            id=_uuid.uuid4(),
            username="carol",
            email=None,
            password_hash="$2b$12$abc",
            role="user",
            is_active=True,
        )
        created = await repo.create(user)
        await db.commit()

        fetched = await repo.get_by_username("carol")
        assert fetched is not None
        assert fetched.id == created.id

    async def test_update_active_status(self, db):
        user = await make_user(db, username="dave", is_active=True)
        await db.commit()

        repo = UserRepository(db)
        updated = await repo.update_active_status(user, False)
        await db.commit()

        assert updated.is_active is False

    async def test_get_app_access_returns_all_rows(self, db):
        user = await make_user(db, username="eve")
        await make_app_access(db, user.id, enabled_apps=["budget-site"])
        await db.commit()

        repo = UserRepository(db)
        rows = await repo.get_app_access(user.id)
        assert len(rows) == len(PROTECTED_APPS)
        enabled = [r for r in rows if r.is_enabled]
        assert len(enabled) == 1
        assert enabled[0].app_name == "budget-site"
