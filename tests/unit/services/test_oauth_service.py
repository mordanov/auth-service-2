import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.oauth_service import GoogleOAuthProvider, GitHubOAuthProvider


class TestGoogleOAuthProvider:
    def test_get_authorization_url_contains_client_id(self):
        provider = GoogleOAuthProvider()
        with patch("services.oauth_service.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "my-client-id"
            mock_settings.GOOGLE_REDIRECT_URI = "https://auth.mainpage.com/callback/google"
            url = provider.get_authorization_url("mystate")
        assert "my-client-id" in url
        assert "mystate" in url
        assert "accounts.google.com" in url

    def test_get_authorization_url_includes_state(self):
        provider = GoogleOAuthProvider()
        with patch("services.oauth_service.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "cid"
            mock_settings.GOOGLE_REDIRECT_URI = "https://example.com/cb"
            url = provider.get_authorization_url("some_state_value")
        assert "some_state_value" in url

    @pytest.mark.asyncio
    async def test_exchange_code_calls_token_endpoint(self):
        provider = GoogleOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"access_token": "gtoken123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.oauth_service.httpx.AsyncClient", return_value=mock_client):
            with patch("services.oauth_service.settings") as s:
                s.GOOGLE_CLIENT_ID = "cid"
                s.GOOGLE_CLIENT_SECRET = "csec"
                s.GOOGLE_REDIRECT_URI = "https://example.com/cb"
                result = await provider.exchange_code("auth_code")

        assert result["access_token"] == "gtoken123"

    @pytest.mark.asyncio
    async def test_get_verified_email_returns_email_and_sub(self):
        provider = GoogleOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "email": "alice@example.com",
            "email_verified": True,
            "sub": "google-sub-123",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.oauth_service.httpx.AsyncClient", return_value=mock_client):
            result = await provider.get_verified_email("access_token_xyz")

        assert result == ("alice@example.com", "google-sub-123")

    @pytest.mark.asyncio
    async def test_get_verified_email_returns_none_for_unverified_email(self):
        provider = GoogleOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "email": "unverified@example.com",
            "email_verified": False,
            "sub": "sub-xyz",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.oauth_service.httpx.AsyncClient", return_value=mock_client):
            result = await provider.get_verified_email("token")

        assert result is None


class TestGitHubOAuthProvider:
    def test_get_authorization_url_contains_client_id(self):
        provider = GitHubOAuthProvider()
        with patch("services.oauth_service.settings") as s:
            s.GITHUB_CLIENT_ID = "gh-cid"
            s.GITHUB_REDIRECT_URI = "https://auth.mainpage.com/callback/github"
            url = provider.get_authorization_url("gh_state")
        assert "gh-cid" in url
        assert "gh_state" in url
        assert "github.com" in url

    @pytest.mark.asyncio
    async def test_get_verified_email_returns_primary_verified(self):
        provider = GitHubOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.oauth_service.httpx.AsyncClient", return_value=mock_client):
            result = await provider.get_verified_email("gh_token")

        assert result == ("primary@example.com", "primary@example.com")

    @pytest.mark.asyncio
    async def test_get_verified_email_returns_none_if_no_primary_verified(self):
        provider = GitHubOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {"email": "unverified@example.com", "primary": True, "verified": False},
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.oauth_service.httpx.AsyncClient", return_value=mock_client):
            result = await provider.get_verified_email("gh_token")

        assert result is None
