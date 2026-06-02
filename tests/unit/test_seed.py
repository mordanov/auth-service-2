import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSeed:
    async def test_seed_skips_when_users_exist(self):
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = object()  # non-None → users exist
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("db.seed.AsyncSessionLocal", return_value=mock_session_ctx):
            from db.seed import seed
            await seed()

        mock_db.commit.assert_not_called()

    async def test_seed_creates_users_when_empty(self):
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # empty table
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        import importlib
        import db.seed as seed_module

        with patch("db.seed.AsyncSessionLocal", return_value=mock_session_ctx):
            with patch("db.seed.settings") as mock_settings:
                mock_settings.ADMIN_USERNAME = "admin"
                mock_settings.ADMIN_PASSWORD = "adminpw"
                mock_settings.USER1_USERNAME = "user1"
                mock_settings.USER1_PASSWORD = "user1pw"
                mock_settings.USER2_USERNAME = "user2"
                mock_settings.USER2_PASSWORD = "user2pw"
                await seed_module.seed()

        mock_db.commit.assert_called_once()
        assert mock_db.add.call_count > 0
