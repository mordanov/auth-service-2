import uuid
import pytest
from passlib.context import CryptContext

from tests.conftest import make_user, make_token, make_app_access
from models.user import PROTECTED_APPS

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_admin_counter = 0


async def _admin_client(client, db):
    """Login as a unique admin user and return cookie dict."""
    global _admin_counter
    _admin_counter += 1
    username = f"admin_user_{_admin_counter}"
    await make_user(
        db,
        username=username,
        password_hash=_pwd.hash("adminpw"),
        role="admin",
    )
    await db.commit()
    resp = await client.post("/api/auth/login", json={"username": username, "password": "adminpw"})
    assert resp.status_code == 200
    return {"auth_token": resp.cookies["auth_token"]}


class TestAdminAuthorization:
    async def test_non_admin_request_returns_403(self, client, db):
        await make_user(db, username="plain_user", password_hash=_pwd.hash("pw"), role="user")
        await db.commit()

        login = await client.post("/api/auth/login", json={"username": "plain_user", "password": "pw"})
        cookies = {"auth_token": login.cookies["auth_token"]}

        resp = await client.get("/api/admin/users", cookies=cookies)
        assert resp.status_code == 403

    async def test_unauthenticated_request_returns_401(self, client, db):
        resp = await client.get("/api/admin/users")
        assert resp.status_code == 401


class TestListUsers:
    async def test_admin_can_list_users(self, client, db):
        cookies = await _admin_client(client, db)
        resp = await client.get("/api/admin/users", cookies=cookies)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCreateUser:
    async def test_admin_can_create_user(self, client, db):
        cookies = await _admin_client(client, db)
        resp = await client.post(
            "/api/admin/users",
            json={"username": "newbie", "password": "pw1234", "role": "user"},
            cookies=cookies,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newbie"
        assert data["is_active"] is True

    async def test_duplicate_username_returns_409(self, client, db):
        cookies = await _admin_client(client, db)
        await client.post(
            "/api/admin/users",
            json={"username": "dup_user", "password": "pw", "role": "user"},
            cookies=cookies,
        )
        resp = await client.post(
            "/api/admin/users",
            json={"username": "dup_user", "password": "pw2", "role": "user"},
            cookies=cookies,
        )
        assert resp.status_code == 409


class TestBlockUser:
    async def test_block_user_invalidates_tokens(self, client, db):
        cookies = await _admin_client(client, db)

        # Create a regular user with a token
        target = await make_user(db, username="to_block", password_hash=_pwd.hash("pw"))
        token = await make_token(db, target.id)
        await db.commit()

        # Verify token is valid before block
        verify_before = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert verify_before.status_code == 200

        # Block the user
        resp = await client.patch(
            f"/api/admin/users/{target.id}",
            json={"is_active": False},
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Token should now be rejected (user blocked + tokens deleted)
        verify_after = await client.get(
            "/api/verify-token",
            cookies={"auth_token": token.token_value},
        )
        assert verify_after.status_code == 401


class TestUnblockUser:
    async def test_unblock_user_sets_active_true(self, client, db):
        cookies = await _admin_client(client, db)
        target = await make_user(db, username="to_unblock", is_active=False)
        await make_app_access(db, target.id)
        await db.commit()

        resp = await client.patch(
            f"/api/admin/users/{target.id}",
            json={"is_active": True},
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    async def test_patch_nonexistent_user_returns_404(self, client, db):
        cookies = await _admin_client(client, db)
        resp = await client.patch(
            f"/api/admin/users/{uuid.uuid4()}",
            json={"is_active": False},
            cookies=cookies,
        )
        assert resp.status_code == 404

    async def test_create_user_invalid_role_returns_422(self, client, db):
        cookies = await _admin_client(client, db)
        resp = await client.post(
            "/api/admin/users",
            json={"username": "badroler", "password": "pw", "role": "admin"},
            cookies=cookies,
        )
        assert resp.status_code == 422

    async def test_get_apps_nonexistent_user_returns_404(self, client, db):
        cookies = await _admin_client(client, db)
        resp = await client.get(f"/api/admin/users/{uuid.uuid4()}/apps", cookies=cookies)
        assert resp.status_code == 404

    async def test_put_apps_nonexistent_user_returns_404(self, client, db):
        cookies = await _admin_client(client, db)
        access = [{"app_name": n, "is_enabled": False} for n in PROTECTED_APPS]
        resp = await client.put(
            f"/api/admin/users/{uuid.uuid4()}/apps",
            json=access,
            cookies=cookies,
        )
        assert resp.status_code == 404


class TestAppAccess:
    async def test_get_app_access_returns_8_rows(self, client, db):
        cookies = await _admin_client(client, db)
        target = await make_user(db, username="apps_user")
        await make_app_access(db, target.id)
        await db.commit()

        resp = await client.get(f"/api/admin/users/{target.id}/apps", cookies=cookies)
        assert resp.status_code == 200
        assert len(resp.json()) == len(PROTECTED_APPS)

    async def test_put_app_access_updates_correctly(self, client, db):
        cookies = await _admin_client(client, db)
        target = await make_user(db, username="apps_put_user")
        await make_app_access(db, target.id)
        await db.commit()

        new_access = [
            {"app_name": name, "is_enabled": name in ("budget-site", "reminders-app")}
            for name in PROTECTED_APPS
        ]
        resp = await client.put(
            f"/api/admin/users/{target.id}/apps",
            json=new_access,
            cookies=cookies,
        )
        assert resp.status_code == 200
        enabled = [r["app_name"] for r in resp.json() if r["is_enabled"]]
        assert set(enabled) == {"budget-site", "reminders-app"}

    async def test_put_incomplete_app_list_returns_422(self, client, db):
        cookies = await _admin_client(client, db)
        target = await make_user(db, username="apps_bad_user")
        await make_app_access(db, target.id)
        await db.commit()

        # Only send 2 apps instead of 8
        incomplete = [
            {"app_name": "budget-site", "is_enabled": True},
            {"app_name": "reminders-app", "is_enabled": False},
        ]
        resp = await client.put(
            f"/api/admin/users/{target.id}/apps",
            json=incomplete,
            cookies=cookies,
        )
        assert resp.status_code == 422
