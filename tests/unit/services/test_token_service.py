import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.token import AuthToken
from models.user import User
from services.token_service import TokenService


def _make_user(is_active: bool = True) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.username = "alice"
    u.role = "user"
    u.is_active = is_active
    return u


def _make_token(user_id, value="abc" * 22, hours: float = 24) -> MagicMock:
    t = MagicMock(spec=AuthToken)
    t.token_value = value
    t.user_id = user_id
    t.expires_at = datetime.utcnow() + timedelta(hours=hours)
    t.last_used_at = None
    return t


class TestGenerateToken:
    async def test_produces_64_hex_chars(self):
        user_id = uuid.uuid4()
        token_repo = AsyncMock()
        user_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            result = await TokenService.generate_token(user_id, db)

        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    async def test_creates_token_with_correct_user_id(self):
        user_id = uuid.uuid4()
        token_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            await TokenService.generate_token(user_id, db)

        token_repo.create.assert_called_once()
        created_token = token_repo.create.call_args[0][0]
        assert created_token.user_id == user_id

    async def test_token_expiry_uses_ttl_from_settings(self):
        user_id = uuid.uuid4()
        token_repo = AsyncMock()
        db = AsyncMock()
        before = datetime.utcnow()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.settings") as mock_settings:
                mock_settings.TOKEN_TTL_HOURS = 12
                await TokenService.generate_token(user_id, db)

        created_token = token_repo.create.call_args[0][0]
        delta = created_token.expires_at - before
        assert timedelta(hours=11, minutes=59) < delta < timedelta(hours=12, minutes=1)


class TestValidateToken:
    async def test_returns_user_for_valid_token(self):
        user = _make_user()
        token = _make_token(user.id)

        token_repo = AsyncMock()
        token_repo.get_by_value.return_value = token
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.UserRepository", return_value=user_repo):
                result = await TokenService.validate_token(token.token_value, db)

        assert result is user

    async def test_returns_none_for_unknown_token(self):
        token_repo = AsyncMock()
        token_repo.get_by_value.return_value = None
        user_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.UserRepository", return_value=user_repo):
                result = await TokenService.validate_token("doesnotexist", db)

        assert result is None

    async def test_returns_none_and_deletes_expired_token(self):
        user = _make_user()
        token = _make_token(user.id, hours=-1)

        token_repo = AsyncMock()
        token_repo.get_by_value.return_value = token
        user_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.UserRepository", return_value=user_repo):
                result = await TokenService.validate_token(token.token_value, db)

        assert result is None
        token_repo.delete.assert_called_once_with(token)

    async def test_returns_none_for_blocked_user(self):
        user = _make_user(is_active=False)
        token = _make_token(user.id)

        token_repo = AsyncMock()
        token_repo.get_by_value.return_value = token
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.UserRepository", return_value=user_repo):
                result = await TokenService.validate_token(token.token_value, db)

        assert result is None

    async def test_returns_none_when_user_not_found(self):
        user_id = uuid.uuid4()
        token = _make_token(user_id)

        token_repo = AsyncMock()
        token_repo.get_by_value.return_value = token
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = None
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            with patch("services.token_service.UserRepository", return_value=user_repo):
                result = await TokenService.validate_token(token.token_value, db)

        assert result is None


class TestCleanupExpired:
    async def test_calls_delete_expired_and_commits(self):
        token_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.token_service.TokenRepository", return_value=token_repo):
            await TokenService.cleanup_expired(db)

        token_repo.delete_expired.assert_called_once()
        db.commit.assert_called_once()
