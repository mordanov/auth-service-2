import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestCleanupTask:
    def test_start_scheduler_adds_job(self):
        from tasks.cleanup import start_scheduler, stop_scheduler, scheduler

        mock_scheduler = MagicMock()
        with patch("tasks.cleanup.scheduler", mock_scheduler):
            start_scheduler()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()

    def test_stop_scheduler_shuts_down_when_running(self):
        from tasks.cleanup import stop_scheduler

        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        with patch("tasks.cleanup.scheduler", mock_scheduler):
            stop_scheduler()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_stop_scheduler_noop_when_not_running(self):
        from tasks.cleanup import stop_scheduler

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        with patch("tasks.cleanup.scheduler", mock_scheduler):
            stop_scheduler()
        mock_scheduler.shutdown.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_job_calls_token_service(self):
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("tasks.cleanup.AsyncSessionLocal", return_value=mock_session_ctx):
            with patch("tasks.cleanup.TokenService.cleanup_expired", new=AsyncMock()) as mock_cleanup:
                from tasks.cleanup import _cleanup_job
                await _cleanup_job()
        mock_cleanup.assert_called_once_with(mock_db)
