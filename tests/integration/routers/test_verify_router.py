import secrets
import pytest
from datetime import datetime, timedelta
from passlib.context import CryptContext

from tests.conftest import make_user, make_token, make_app_access
from models.token import AuthToken

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestVerifyTokenEndpoint:
    async def test_valid_cookie_returns_200_with_correct_fields(self, client, db):
        user = await make_user(db, username="verify_ok", password_hash=_pwd.hash("pw"))
        await make_app_access(db, user.id, enabled_apps=["budget-site", "reminders-app"])
        token = await make_token(db, user.id)
        await db.commit()

        resp = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "verify_ok"
        assert data["role"] == "user"
        assert set(data["apps"]) == {"budget-site", "reminders-app"}

    async def test_bearer_token_accepted(self, client, db):
        user = await make_user(db, username="verify_bearer")
        await make_app_access(db, user.id)
        token = await make_token(db, user.id)
        await db.commit()

        resp = await client.get(
            "/api/verify-token",
            headers={"Authorization": f"Bearer {token.token_value}"},
        )
        assert resp.status_code == 200

    async def test_expired_token_returns_401(self, client, db):
        user = await make_user(db, username="verify_expired")
        await make_app_access(db, user.id)
        token = await make_token(db, user.id, hours=-1)
        await db.commit()

        resp = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "unauthorized"

    async def test_no_token_returns_401(self, client, db):
        resp = await client.get("/api/verify-token")
        assert resp.status_code == 401

    async def test_invalid_token_value_returns_401(self, client, db):
        resp = await client.get(
            "/api/verify-token",
            cookies={"auth_token": "nonexistenttoken"},
        )
        assert resp.status_code == 401

    async def test_blocked_user_token_returns_401(self, client, db):
        user = await make_user(db, username="verify_blocked", is_active=False)
        await make_app_access(db, user.id)
        token = await make_token(db, user.id)
        await db.commit()

        resp = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert resp.status_code == 401

    async def test_apps_array_matches_enabled_access_rows(self, client, db):
        user = await make_user(db, username="verify_apps")
        await make_app_access(
            db, user.id,
            enabled_apps=["budget-site", "new-site", "servinga-dashboard"],
        )
        token = await make_token(db, user.id)
        await db.commit()

        resp = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert resp.status_code == 200
        assert set(resp.json()["apps"]) == {"budget-site", "new-site", "servinga-dashboard"}
