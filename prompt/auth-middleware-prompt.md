# Prompt for Generating an Auth Middleware Web Application

## Context and Goal

Create a centralized authentication web application (`auth-app`) that serves as a **single entry point** for a group of existing family web applications. The application acts as a "front door": all protected applications delegate authentication to this service via opaque token verification.

---

## Directory Structure

```
~/web-folders/          ← main directory: nginx configs, postgres, .env
../auth-app/            ← application to be created (same level as web-folders)
../budget-site/
../family-admin-routine/
../family-archive/
../family-kitchen-recipes/
../new-site/
../portuguese-expenses/
../reminders-app/
../servinga-dashboard/
```

---

## Technology Stack

| Layer       | Technology                                                  |
|-------------|-------------------------------------------------------------|
| Frontend    | React.js + HeroUI (default design, no customization)        |
| Backend     | Python 3.12 + FastAPI                                       |
| Database    | PostgreSQL from `web-folders`                               |
| Web Server  | Nginx from `web-folders`                                    |
| Containers  | Docker + docker-compose (same pattern as other applications)|
| i18n        | Russian and English (language switcher in UI)               |

---

## Roles and Access

### Role `admin`
- Access **only** to `auth-app`
- Create users (deletion not supported, only blocking)
- Manage access: per-user checkboxes to enable/disable access to each of the 8 applications
- View full user list with statuses

### Role `user`
- Access to protected applications according to assigned permissions
- Cannot create other users
- No access to the admin panel

---

## Authentication Methods

### 1. Login/Password
- Password storage: bcrypt hash in PostgreSQL
- On first run, a `db seed` / migration creates 3 users from `.env`:
  ```
  ADMIN_USERNAME=...
  ADMIN_PASSWORD=...
  USER1_USERNAME=...
  USER1_PASSWORD=...
  USER2_USERNAME=...
  USER2_PASSWORD=...
  ```

### 2. Google OAuth2
- Login only for users who already have an account in the DB with a matching email
- Unknown users are denied access (no auto-registration)

### 3. GitHub OAuth
- Same as Google: only pre-created accounts (matched by email)
- Unknown users are denied access

---

## Token Mechanism (Opaque Token)

- After successful authentication, a random opaque token is generated (e.g. 64-character string)
- Token is stored in the `auth_tokens` table in PostgreSQL:
  ```
  token_value, user_id, expires_at, created_at, app_name
  ```
- Token TTL: configurable via `.env` (`TOKEN_TTL_HOURS`, default: 24 hours)
- Token is delivered to the client via httpOnly cookie (`auth_token`)

### Token Verification Endpoints (for protected applications)
```
GET /api/verify-token
Headers: Cookie: auth_token=<token>  OR  Authorization: Bearer <token>

Response 200: { "user_id": "...", "username": "...", "role": "user", "apps": ["budget-site", ...] }
Response 401: { "error": "unauthorized" }
```

---

## Integration with Protected Applications

### For each of the 8 applications:

1. **Remove** existing authentication logic (login pages, session checks, password middleware)
2. **Add** middleware/decorator to every protected route:

#### Python (FastAPI) — example middleware:
```python
# auth_middleware.py
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

AUTH_SERVICE_URL = "https://auth.mainpage.com"
VERIFY_ENDPOINT = f"{AUTH_SERVICE_URL}/api/verify-token"

async def require_auth(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return RedirectResponse(url=f"{AUTH_SERVICE_URL}/login?redirect={request.url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(VERIFY_ENDPOINT, cookies={"auth_token": token})
    if resp.status_code != 200:
        return RedirectResponse(url=f"{AUTH_SERVICE_URL}/login?redirect={request.url}")
    return resp.json()
```

#### React (Frontend) — example client-side check:
```javascript
// useAuth.js
export async function checkAuth() {
  const res = await fetch('https://auth.mainpage.com/api/verify-token', {
    credentials: 'include'
  });
  if (!res.ok) {
    window.location.href = `https://auth.mainpage.com/login?redirect=${window.location.href}`;
    return null;
  }
  return res.json();
}
```

3. **Ensure** the `auth_token` cookie is sent by the browser with requests (`SameSite=Lax`, `Secure`, domain `.mainpage.com`)

---

## Nginx Configuration

Add to `web-folders` nginx configs:

### auth.mainpage.com
```nginx
server {
    listen 443 ssl;
    server_name auth.mainpage.com;
    location / {
        proxy_pass http://auth-app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### For each protected application (example: budget.mainpage.com)
```nginx
server {
    listen 443 ssl;
    server_name budget.mainpage.com;
    location / {
        proxy_pass http://budget-site:PORT;
        proxy_cookie_domain auth.mainpage.com .mainpage.com;
    }
}
```

---

## auth-app Structure

```
auth-app/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py          # /login, /logout, /callback/google, /callback/github
│   │   ├── verify.py        # /api/verify-token
│   │   └── admin.py         # /api/admin/users, /api/admin/apps
│   ├── models/
│   │   ├── user.py
│   │   └── token.py
│   ├── db/
│   │   ├── database.py      # connection to postgres from web-folders
│   │   └── seed.py          # create initial users from .env
│   └── middleware/
│       └── auth_check.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── i18n/
│   │   │   ├── ru.json
│   │   │   └── en.json
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx      # login form + Google/GitHub buttons
│   │   │   └── AdminPage.jsx      # user and access management
│   │   └── components/
│   │       ├── UserTable.jsx
│   │       ├── AppAccessCheckboxes.jsx
│   │       └── LanguageSwitcher.jsx
```

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),          -- NULL for OAuth-only users
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT TRUE,
    google_id VARCHAR(255),
    github_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Application access
CREATE TABLE user_app_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    app_name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, app_name)
);

-- Tokens
CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_value VARCHAR(128) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);
```

---

## .env.example

```env
# Database (from web-folders)
DATABASE_URL=postgresql://user:password@postgres:5432/maindb

# Initial users
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_admin
USER1_USERNAME=user1
USER1_PASSWORD=change_me_user1
USER2_USERNAME=user2
USER2_PASSWORD=change_me_user2

# Tokens
TOKEN_TTL_HOURS=24
SECRET_KEY=change_me_secret

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://auth.mainpage.com/callback/google

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=https://auth.mainpage.com/callback/github

# Domain
AUTH_APP_URL=https://auth.mainpage.com
COOKIE_DOMAIN=.mainpage.com
```

---

## UI (Frontend — HeroUI default)

Use **HeroUI components without style customization**. Implement:

### Login Page (`/login`)
- Tabs: "Sign in with password" / "Google" / "GitHub"
- Fields: username/email + password
- OAuth buttons with provider icons
- Language switcher (RU / EN) in the top-right corner

### Admin Panel (`/admin`) — `admin` role only
- User table: name, email, role, status (active / blocked)
- Buttons: "Create user", "Block"
- Expanding a user row reveals checkboxes for access to 8 applications

---

## Protected Applications (list)

- `budget-site`
- `family-admin-routine`
- `family-archive`
- `family-kitchen-recipes`
- `new-site`
- `portuguese-expenses`
- `reminders-app`
- `servinga-dashboard`

---

## Additional Requirements

- All API endpoints must have OpenAPI documentation (FastAPI `/docs`)
- Expired tokens are deleted by a background task (APScheduler or FastAPI background tasks)
- Login attempts (successful and failed) are logged to a separate `auth_logs` table
- CORS configured for `*.mainpage.com` domains
- All secrets via `.env` only, never hardcoded
