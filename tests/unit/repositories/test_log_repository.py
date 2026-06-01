import uuid
import pytest

from repositories.log_repository import LogRepository
from models.log import AuthLog


class TestLogRepository:
    async def test_create_inserts_all_fields(self, db):
        repo = LogRepository(db)
        log = AuthLog(
            username="alice",
            ip_address="127.0.0.1",
            method="password",
            success=True,
            reason=None,
        )
        result = await repo.create(log)
        await db.commit()

        assert result.username == "alice"
        assert result.ip_address == "127.0.0.1"
        assert result.method == "password"
        assert result.success is True
        assert result.reason is None

    async def test_create_failure_log(self, db):
        repo = LogRepository(db)
        log = AuthLog(
            username="bob",
            ip_address=None,
            method="google",
            success=False,
            reason="unknown_oauth_email",
        )
        result = await repo.create(log)
        await db.commit()

        assert result.success is False
        assert result.reason == "unknown_oauth_email"

    def test_no_update_or_delete_methods_on_class(self):
        # Verify LogRepository has no UPDATE or DELETE operations — insert-only
        assert not hasattr(LogRepository, "update")
        assert not hasattr(LogRepository, "delete")
        assert not hasattr(LogRepository, "update_log")
        assert not hasattr(LogRepository, "delete_log")
