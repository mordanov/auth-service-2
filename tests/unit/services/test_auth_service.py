import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from models.user import User
from services.auth_service import AuthService


def _make_user(
    username: str = "alice",
    password: str = "secret",
    is_active: bool = True,
    email: str = "alice@example.com",
    role: str = "user",
) -> User:
    from services.pwd import hash_password
    return User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=is_active,
        role=role,
        google_id=None,
        github_id=None,
    )


# ── Password login ───────────────────────────────────────────────────────────

class TestPasswordLogin:
    async def test_valid_credentials_returns_token(self):
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                with patch("services.auth_service.TokenService.generate_token", new=AsyncMock(return_value="token123")):
                    token, reason = await AuthService.login("alice", "secret", db)

        assert token == "token123"
        assert reason is None
        log_repo.create.assert_called_once()
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is True

    async def test_wrong_password_returns_none_and_logs_failure(self):
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                token, reason = await AuthService.login("alice", "wrongpassword", db)

        assert token is None
        assert reason == "invalid_credentials"
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is False
        assert log_entry.reason == "invalid_credentials"

    async def test_unknown_user_returns_none_and_logs_failure(self):
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = None
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                token, reason = await AuthService.login("nobody", "secret", db)

        assert token is None
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is False

    async def test_blocked_user_returns_none_and_logs_failure(self):
        user = _make_user(is_active=False)
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                token, reason = await AuthService.login("alice", "secret", db)

        assert token is None
        assert reason == "user_blocked"
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is False
        assert log_entry.reason == "user_blocked"

    async def test_never_logs_plaintext_password(self):
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_username.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()
        logged_objects = []

        async def capture_create(log_entry):
            logged_objects.append(log_entry)

        log_repo.create.side_effect = capture_create

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                with patch("services.auth_service.TokenService.generate_token", new=AsyncMock(return_value="tok")):
                    await AuthService.login("alice", "mysecretpassword", db)

        for obj in logged_objects:
            obj_dict = vars(obj)
            for val in obj_dict.values():
                assert "mysecretpassword" not in str(val)


# ── OAuth login ──────────────────────────────────────────────────────────────

class TestOAuthLogin:
    async def test_known_email_issues_token(self):
        user = _make_user(email="alice@example.com")
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                with patch("services.auth_service.TokenService.generate_token", new=AsyncMock(return_value="oauthtoken")):
                    result = await AuthService.oauth_login("google", "alice@example.com", "google-id-1", db)

        assert result == "oauthtoken"

    async def test_unknown_email_returns_none_and_logs_failure(self):
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                result = await AuthService.oauth_login("google", "unknown@example.com", "google-id-x", db)

        assert result is None
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is False
        assert log_entry.reason == "unknown_oauth_email"

    async def test_blocked_user_returns_none(self):
        user = _make_user(is_active=False, email="alice@example.com")
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                result = await AuthService.oauth_login("google", "alice@example.com", "google-id", db)

        assert result is None
        log_entry = log_repo.create.call_args[0][0]
        assert log_entry.success is False
        assert log_entry.reason == "user_blocked"

    async def test_google_id_stored_on_first_login(self):
        user = _make_user(email="alice@example.com")
        assert user.google_id is None
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                with patch("services.auth_service.TokenService.generate_token", new=AsyncMock(return_value="tok")):
                    await AuthService.oauth_login("google", "alice@example.com", "gid-42", db)

        assert user.google_id == "gid-42"

    async def test_github_id_stored_on_first_login(self):
        user = _make_user(email="alice@example.com")
        assert user.github_id is None
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        log_repo = AsyncMock()
        db = AsyncMock()

        with patch("services.auth_service.UserRepository", return_value=user_repo):
            with patch("services.auth_service.LogRepository", return_value=log_repo):
                with patch("services.auth_service.TokenService.generate_token", new=AsyncMock(return_value="tok")):
                    await AuthService.oauth_login("github", "alice@example.com", "ghid-77", db)

        assert user.github_id == "ghid-77"
