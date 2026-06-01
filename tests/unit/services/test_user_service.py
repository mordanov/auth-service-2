import uuid
from unittest.mock import AsyncMock, patch, call

import pytest

from models.user import User, UserAppAccess, PROTECTED_APPS
from schemas.user import UserCreate, AppAccessItem
from services.user_service import UserService


def _make_user(username: str = "newuser", is_active: bool = True) -> User:
    return User(
        id=uuid.uuid4(),
        username=username,
        email=None,
        password_hash="hashed",
        role="user",
        is_active=is_active,
        google_id=None,
        github_id=None,
    )


class TestCreateUser:
    async def test_creates_user_with_hashed_password(self):
        data = UserCreate(username="newuser", password="plaintext", role="user")
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = None
        user_repo.get_by_email.return_value = None

        created_user = _make_user()
        user_repo.create.return_value = created_user
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        with patch("services.user_service.UserRepository", return_value=user_repo):
            result = await UserService.create_user(data, db)

        assert result is created_user
        user_arg = user_repo.create.call_args[0][0]
        assert user_arg.password_hash != "plaintext"
        assert user_arg.password_hash.startswith("$2b$")

    async def test_inserts_8_app_access_rows_with_is_enabled_false(self):
        from unittest.mock import MagicMock
        data = UserCreate(username="newuser", password="pw", role="user")
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = None
        user_repo.get_by_email.return_value = None

        created_user = _make_user()
        user_repo.create.return_value = created_user

        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        added_objects = []
        db.add = MagicMock(side_effect=added_objects.append)

        with patch("services.user_service.UserRepository", return_value=user_repo):
            await UserService.create_user(data, db)

        access_rows = [obj for obj in added_objects if isinstance(obj, UserAppAccess)]
        assert len(access_rows) == 8
        assert all(not row.is_enabled for row in access_rows)
        added_app_names = {row.app_name for row in access_rows}
        assert added_app_names == set(PROTECTED_APPS)

    async def test_raises_if_username_taken(self):
        data = UserCreate(username="existing", password="pw", role="user")
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = _make_user("existing")
        db = AsyncMock()

        with patch("services.user_service.UserRepository", return_value=user_repo):
            with pytest.raises(ValueError, match="username already exists"):
                await UserService.create_user(data, db)


class TestBlockUser:
    async def test_sets_is_active_false_and_deletes_tokens(self):
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        user_repo.update_active_status.return_value = user

        token_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.user_service.UserRepository", return_value=user_repo):
            with patch("services.user_service.TokenRepository", return_value=token_repo):
                result = await UserService.block_user(user.id, db)

        token_repo.delete_by_user_id.assert_called_once_with(user.id)
        user_repo.update_active_status.assert_called_once_with(user, False)
        db.commit.assert_called_once()

    async def test_delete_tokens_and_set_inactive_in_same_call_sequence(self):
        user = _make_user()
        call_order = []

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        async def track_update(u, active):
            call_order.append("update_active_status")
            return u

        user_repo.update_active_status.side_effect = track_update

        token_repo = AsyncMock()

        async def track_delete(uid):
            call_order.append("delete_by_user_id")

        token_repo.delete_by_user_id.side_effect = track_delete
        db = AsyncMock()

        with patch("services.user_service.UserRepository", return_value=user_repo):
            with patch("services.user_service.TokenRepository", return_value=token_repo):
                await UserService.block_user(user.id, db)

        assert call_order == ["delete_by_user_id", "update_active_status"]

    async def test_raises_if_user_not_found(self):
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = None
        token_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.user_service.UserRepository", return_value=user_repo):
            with patch("services.user_service.TokenRepository", return_value=token_repo):
                with pytest.raises(ValueError, match="user_not_found"):
                    await UserService.block_user(uuid.uuid4(), db)


class TestUpdateAppAccess:
    async def test_upserts_all_8_rows_correctly(self):
        user_id = uuid.uuid4()
        app_list = [AppAccessItem(app_name=n, is_enabled=(n == "budget-site")) for n in PROTECTED_APPS]

        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import AsyncMock, MagicMock, patch

        db = AsyncMock(spec=AsyncSession)

        existing_rows = [
            UserAppAccess(user_id=user_id, app_name=app_name, is_enabled=False)
            for app_name in PROTECTED_APPS
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = existing_rows
        db.execute.return_value = mock_result

        await UserService.update_app_access(user_id, app_list, db)

        budget_row = next(r for r in existing_rows if r.app_name == "budget-site")
        other_rows = [r for r in existing_rows if r.app_name != "budget-site"]
        assert budget_row.is_enabled is True
        assert all(not r.is_enabled for r in other_rows)
