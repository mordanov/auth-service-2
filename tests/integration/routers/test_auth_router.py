import uuid
import pytest

from tests.conftest import make_user, make_token, make_app_access
from services.pwd import hash_password


class TestLoginEndpoint:
    async def test_valid_credentials_sets_cookie(self, client, db):
        await make_user(db, username="login_ok", password_hash=hash_password("pass123"))
        await db.commit()

        resp = await client.post("/api/auth/login", json={"username": "login_ok", "password": "pass123"})
        assert resp.status_code == 200
        assert "auth_token" in resp.cookies

    async def test_wrong_password_returns_401(self, client, db):
        await make_user(db, username="login_bad", password_hash=hash_password("correct"))
        await db.commit()

        resp = await client.post("/api/auth/login", json={"username": "login_bad", "password": "wrong"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "invalid_credentials"

    async def test_unknown_user_returns_401(self, client, db):
        resp = await client.post("/api/auth/login", json={"username": "nobody_xyz", "password": "pw"})
        assert resp.status_code == 401

    async def test_blocked_user_returns_403(self, client, db):
        await make_user(db, username="login_blocked", password_hash=hash_password("pw"), is_active=False)
        await db.commit()

        resp = await client.post("/api/auth/login", json={"username": "login_blocked", "password": "pw"})
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "forbidden"


class TestLogoutEndpoint:
    async def test_logout_clears_cookie(self, client, db):
        user = await make_user(db, username="logout_user", password_hash=hash_password("pw"))
        await db.commit()

        # login first
        login_resp = await client.post("/api/auth/login", json={"username": "logout_user", "password": "pw"})
        assert login_resp.status_code == 200

        # logout
        logout_resp = await client.post("/api/auth/logout")
        assert logout_resp.status_code == 200

    async def test_logout_without_cookie_returns_200(self, client, db):
        resp = await client.post("/api/auth/logout")
        assert resp.status_code == 200


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client, db):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


