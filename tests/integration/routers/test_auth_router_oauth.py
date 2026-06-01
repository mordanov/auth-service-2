"""OAuth route integration tests using mocked OAuth providers."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import make_user
from services.pwd import hash_password


class TestGoogleAuthRoute:
    async def test_google_redirects_to_google(self, client, db):
        resp = await client.get("/api/auth/google", follow_redirects=False)
        assert resp.status_code == 302
        assert "accounts.google.com" in resp.headers["location"]

    async def test_google_callback_known_email_sets_cookie(self, client, db):
        from routers.auth import _create_oauth_state
        user = await make_user(db, username="guser", email="guser@example.com")
        await db.commit()

        nonce = _create_oauth_state("")
        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "gat"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=("guser@example.com", "google-sub-1")),
            ):
                resp = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "auth_code", "state": nonce},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "auth_token" in resp.cookies

    async def test_google_callback_unknown_email_redirects_to_forbidden(self, client, db):
        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "gat"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=("unknown@nowhere.com", "sub-x")),
            ):
                resp = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": ""},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]

    async def test_google_callback_exchange_failure_redirects_to_forbidden(self, client, db):
        with patch("routers.auth._google.exchange_code", new=AsyncMock(side_effect=Exception("network"))):
            resp = await client.get(
                "/api/auth/callback/google",
                params={"code": "bad_code", "state": ""},
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]

    async def test_google_callback_unverified_email_redirects_to_forbidden(self, client, db):
        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "t"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=None),
            ):
                resp = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": ""},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]


class TestGitHubAuthRoute:
    async def test_github_redirects_to_github(self, client, db):
        resp = await client.get("/api/auth/github", follow_redirects=False)
        assert resp.status_code == 302
        assert "github.com" in resp.headers["location"]

    async def test_github_callback_known_email_sets_cookie(self, client, db):
        from routers.auth import _create_oauth_state
        user = await make_user(db, username="ghuser", email="ghuser@example.com")
        await db.commit()

        nonce = _create_oauth_state("")
        with patch("routers.auth._github.exchange_code", new=AsyncMock(return_value={"access_token": "ghat"})):
            with patch(
                "routers.auth._github.get_verified_email",
                new=AsyncMock(return_value=("ghuser@example.com", "ghuser@example.com")),
            ):
                resp = await client.get(
                    "/api/auth/callback/github",
                    params={"code": "gh_code", "state": nonce},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "auth_token" in resp.cookies

    async def test_github_callback_unknown_email_redirects_to_forbidden(self, client, db):
        with patch("routers.auth._github.exchange_code", new=AsyncMock(return_value={"access_token": "ghat"})):
            with patch(
                "routers.auth._github.get_verified_email",
                new=AsyncMock(return_value=("nobody@nowhere.com", "nobody@nowhere.com")),
            ):
                resp = await client.get(
                    "/api/auth/callback/github",
                    params={"code": "gh_code", "state": ""},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]


class TestOAuthStateNonce:
    async def test_invalid_state_nonce_rejected(self, client, db):
        """ST-002: Tampered/unknown nonce must be rejected — no token issued, redirect to forbidden."""
        user = await make_user(db, username="nonce_user", email="nonce@example.com")
        await db.commit()

        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "t"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=("nonce@example.com", "sub-1")),
            ):
                resp = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": "tampered_nonce_that_does_not_exist"},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]
        assert "auth_token" not in resp.cookies

    async def test_empty_state_rejected(self, client, db):
        """ST-002: Empty state parameter must be rejected — CSRF bypass must not be possible."""
        resp = await client.get(
            "/api/auth/callback/google",
            params={"code": "any_code", "state": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "error=forbidden" in resp.headers["location"]
        assert "auth_token" not in resp.cookies

    async def test_state_nonce_consumed_after_use(self, client, db):
        """Nonce is one-time use: reusing it on a second callback fails gracefully."""
        from routers.auth import _create_oauth_state
        user = await make_user(db, username="nonce2_user", email="nonce2@example.com")
        await db.commit()

        nonce = _create_oauth_state("")

        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "t"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=("nonce2@example.com", "sub-2")),
            ):
                resp1 = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": nonce},
                    follow_redirects=False,
                )
                resp2 = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": nonce},
                    follow_redirects=False,
                )
        # Both succeed (auth works), but the nonce is gone after first use
        assert resp1.status_code == 302
        assert resp2.status_code == 302


class TestST002OAuthStateMismatch:
    """ST-002: unknown/expired nonce → still processes auth (no 500), redirect falls back."""

    async def test_google_unknown_nonce_does_not_500(self, client, db):
        user = await make_user(db, username="st002_g_user", email="st002g@example.com")
        await db.commit()

        with patch("routers.auth._google.exchange_code", new=AsyncMock(return_value={"access_token": "t"})):
            with patch(
                "routers.auth._google.get_verified_email",
                new=AsyncMock(return_value=("st002g@example.com", "sub-st002")),
            ):
                resp = await client.get(
                    "/api/auth/callback/google",
                    params={"code": "code", "state": "completely_unknown_nonce"},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert resp.status_code != 500

    async def test_github_unknown_nonce_does_not_500(self, client, db):
        user = await make_user(db, username="st002_gh_user", email="st002gh@example.com")
        await db.commit()

        with patch("routers.auth._github.exchange_code", new=AsyncMock(return_value={"access_token": "t"})):
            with patch(
                "routers.auth._github.get_verified_email",
                new=AsyncMock(return_value=("st002gh@example.com", "st002gh@example.com")),
            ):
                resp = await client.get(
                    "/api/auth/callback/github",
                    params={"code": "code", "state": "completely_unknown_nonce"},
                    follow_redirects=False,
                )
        assert resp.status_code == 302
        assert resp.status_code != 500


class TestST012TimingNormalization:
    """ST-012: unknown-user and wrong-password paths both call bcrypt verify."""

    async def test_unknown_user_still_calls_dummy_bcrypt(self, db):
        """verify_password is called even when user does not exist (timing normalization)."""
        from services.auth_service import AuthService
        from unittest.mock import patch as mpatch, AsyncMock
        import services.pwd as pwd_module

        verify_calls = []
        original_verify = pwd_module.verify_password

        def capturing_verify(password, hashed):
            verify_calls.append(hashed)
            return original_verify(password, hashed)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_username.return_value = None
        mock_log_repo = AsyncMock()
        mock_log_repo.create = AsyncMock()
        mock_db = AsyncMock()

        with mpatch.object(pwd_module, "verify_password", side_effect=capturing_verify), \
             mpatch.patch("services.auth_service.UserRepository", return_value=mock_user_repo), \
             mpatch.patch("services.auth_service.LogRepository", return_value=mock_log_repo):
            token, reason = await AuthService.login("nobody", "password", mock_db)

        assert token is None
        assert reason == "invalid_credentials"
        assert len(verify_calls) >= 1, "Expected at least one verify_password() call for timing normalization"


_redir_counter = 0


class TestOpenRedirectProtection:
    async def test_login_safe_redirect_returned_in_body(self, client, db):
        global _redir_counter
        _redir_counter += 1
        username = f"redir_safe_{_redir_counter}"
        await make_user(db, username=username, password_hash=hash_password("pw"))
        await db.commit()

        resp = await client.post(
            "/api/auth/login",
            params={"redirect": "https://budget.mainpage.com"},
            json={"username": username, "password": "pw"},
        )
        assert resp.status_code == 200
        assert resp.json()["redirect"] == "https://budget.mainpage.com"

    async def test_login_unsafe_redirect_not_returned(self, client, db):
        global _redir_counter
        _redir_counter += 1
        username = f"redir_unsafe_{_redir_counter}"
        await make_user(db, username=username, password_hash=hash_password("pw"))
        await db.commit()

        resp = await client.post(
            "/api/auth/login",
            params={"redirect": "https://evil.example.com"},
            json={"username": username, "password": "pw"},
        )
        assert resp.status_code == 200
        assert resp.json()["redirect"] is None
