import uuid
import secrets
from datetime import datetime, timedelta

import pytest

from tests.conftest import make_user, make_token
from repositories.token_repository import TokenRepository
from models.token import AuthToken


class TestTokenRepository:
    async def test_create_persists_token(self, db):
        user = await make_user(db, username="tk_create")
        await db.commit()

        repo = TokenRepository(db)
        token = AuthToken(
            token_value=secrets.token_hex(32),
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        created = await repo.create(token)
        await db.commit()

        fetched = await repo.get_by_value(created.token_value)
        assert fetched is not None
        assert fetched.user_id == user.id

    async def test_get_by_value_hit(self, db):
        user = await make_user(db, username="tk_hit")
        token = await make_token(db, user.id)
        await db.commit()

        repo = TokenRepository(db)
        result = await repo.get_by_value(token.token_value)
        assert result is not None
        assert result.token_value == token.token_value

    async def test_get_by_value_miss(self, db):
        repo = TokenRepository(db)
        result = await repo.get_by_value("totally_unknown_value")
        assert result is None

    async def test_delete_removes_token(self, db):
        user = await make_user(db, username="tk_delete")
        token = await make_token(db, user.id)
        await db.commit()

        repo = TokenRepository(db)
        fetched = await repo.get_by_value(token.token_value)
        await repo.delete(fetched)
        await db.commit()

        assert await repo.get_by_value(token.token_value) is None

    async def test_delete_by_user_id_removes_all_user_tokens(self, db):
        user = await make_user(db, username="tk_del_user")
        t1 = await make_token(db, user.id)
        t2 = await make_token(db, user.id)
        await db.commit()

        repo = TokenRepository(db)
        await repo.delete_by_user_id(user.id)
        await db.commit()

        assert await repo.get_by_value(t1.token_value) is None
        assert await repo.get_by_value(t2.token_value) is None

    async def test_delete_expired_leaves_valid_tokens_intact(self, db):
        user = await make_user(db, username="tk_exp")
        valid_token = await make_token(db, user.id, hours=24)
        expired_token = await make_token(db, user.id, hours=-1)
        await db.commit()

        repo = TokenRepository(db)
        await repo.delete_expired(datetime.utcnow())
        await db.commit()

        assert await repo.get_by_value(valid_token.token_value) is not None
        assert await repo.get_by_value(expired_token.token_value) is None
