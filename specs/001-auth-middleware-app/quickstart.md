# Quickstart: Centralized Authentication Gateway

This document is the validation checklist for the completed implementation.
Run through each section end-to-end after deployment to confirm the system
works as specified.

---

## Prerequisites

- `web-folders` PostgreSQL and Nginx are running.
- `auth-app` containers are running (`docker-compose up -d`).
- `.env` is populated with real values (see `.env.example`).
- Alembic migrations have run: `docker exec auth-app-backend alembic upgrade head`.
- Seed script has run: `docker exec auth-app-backend python db/seed.py`.

---

## 1. Health Check

```bash
curl -f https://auth.mainpage.com/health
# Expected: {"status": "ok"}
```

---

## 2. Password Login

```bash
# Successful login
curl -c cookies.txt -X POST https://auth.mainpage.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<ADMIN_PASSWORD from .env>"}'
# Expected: 200 {"message": "ok"}
# Expected: Set-Cookie header with auth_token

# Failed login
curl -X POST https://auth.mainpage.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "wrong"}'
# Expected: 401 {"error": "invalid_credentials"}
```

---

## 3. Token Verification

```bash
# Using cookie from previous login
curl -b cookies.txt https://auth.mainpage.com/api/verify-token
# Expected: 200 {"user_id": "...", "username": "admin", "role": "admin", "apps": [...]}

# No token
curl https://auth.mainpage.com/api/verify-token
# Expected: 401 {"error": "unauthorized"}
```

---

## 4. Admin Panel — User Management

```bash
# List users (admin token required)
curl -b cookies.txt https://auth.mainpage.com/api/admin/users
# Expected: 200 array of user objects

# Create a new user
curl -b cookies.txt -X POST https://auth.mainpage.com/api/admin/users \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123", "role": "user"}'
# Expected: 201

# Get app access for the new user (replace <uuid> with actual id)
curl -b cookies.txt https://auth.mainpage.com/api/admin/users/<uuid>/apps
# Expected: 200, all 8 apps with is_enabled: false

# Enable budget-site access
curl -b cookies.txt -X PUT https://auth.mainpage.com/api/admin/users/<uuid>/apps \
  -H "Content-Type: application/json" \
  -d '[
    {"app_name": "budget-site", "is_enabled": true},
    {"app_name": "family-admin-routine", "is_enabled": false},
    {"app_name": "family-archive", "is_enabled": false},
    {"app_name": "family-kitchen-recipes", "is_enabled": false},
    {"app_name": "new-site", "is_enabled": false},
    {"app_name": "portuguese-expenses", "is_enabled": false},
    {"app_name": "reminders-app", "is_enabled": false},
    {"app_name": "servinga-dashboard", "is_enabled": false}
  ]'
# Expected: 200
```

---

## 5. Block a User and Verify Token Invalidation

```bash
# Login as testuser to get a token
curl -c user_cookies.txt -X POST https://auth.mainpage.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# Verify token works before blocking
curl -b user_cookies.txt https://auth.mainpage.com/api/verify-token
# Expected: 200

# Block the user (admin session)
curl -b cookies.txt -X PATCH https://auth.mainpage.com/api/admin/users/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
# Expected: 200 {"is_active": false}

# Verify the previously-valid token is now rejected
curl -b user_cookies.txt https://auth.mainpage.com/api/verify-token
# Expected: 401 {"error": "unauthorized"}
```

---

## 6. Logout

```bash
curl -b cookies.txt -c cookies.txt -X POST https://auth.mainpage.com/api/auth/logout
# Expected: 200 {"message": "ok"}
# Expected: auth_token cookie cleared

curl -b cookies.txt https://auth.mainpage.com/api/verify-token
# Expected: 401 {"error": "unauthorized"}
```

---

## 7. OAuth (Manual Browser Test)

1. Open `https://auth.mainpage.com/login` in a browser.
2. Click "Sign in with Google" (or GitHub).
3. Complete the provider's authorization flow.
4. **Case A — known email**: Verify redirect to the target application with
   an `auth_token` cookie set.
5. **Case B — unknown email**: Verify the user lands on
   `/login?error=forbidden`.

---

## 8. UI Language Switcher

1. Open `https://auth.mainpage.com/login`.
2. Verify the page loads in the browser's preferred language.
3. Toggle the language switcher (RU ↔ EN).
4. Reload the page; verify the selected language is preserved (from
   `localStorage`).

---

## 9. Test Coverage Gates

```bash
# Backend
docker exec auth-app-backend pytest --cov=. --cov-fail-under=80
# Expected: exit code 0

# Frontend
docker exec auth-app-frontend npm run test:coverage
# Expected: exit code 0, line coverage ≥ 80%
```

---

## 10. Protected Application Integration Smoke Test

On a sample protected application (e.g., `budget-site`) after integrating
`auth_middleware.py`:

1. Clear all cookies.
2. Navigate to `https://budget.mainpage.com`.
3. Verify redirect to `https://auth.mainpage.com/login?redirect=https://budget.mainpage.com`.
4. Log in as a user with `budget-site` access.
5. Verify redirect back to `https://budget.mainpage.com` with application
   content visible.
6. Log in as a user without `budget-site` access.
7. Verify the application returns an appropriate error (protected app is
   responsible for enforcing the `apps` list from the verify-token response).
