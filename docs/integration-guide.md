# Auth-App Integration Guide

This guide explains how to integrate an existing protected application with `auth-app`.
After integration, the protected application relies entirely on `auth-app` for authentication
and removes any local login logic.

## How It Works

```
Browser ──→ Protected App ──→ GET /api/verify-token ──→ auth-app
                                    ↑
                          httpOnly auth_token cookie
                          (shared domain .mainpage.com)
```

1. Every incoming request to a protected app passes through auth middleware.
2. The middleware calls `GET /api/verify-token` on `auth-app` with the `auth_token` cookie forwarded.
3. On `200`, the response includes `user_id`, `username`, `role`, and `apps`.
4. The protected app checks whether its own `app_name` appears in the `apps` array.
5. On `401`, the middleware redirects the user to `https://auth.mainpage.com/login?redirect=<original-url>`.

## Token Verification Response

```
GET /api/verify-token
Cookie: auth_token=<64-hex-char token>

200 OK
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "role": "user",
  "apps": ["budget-site", "family-archive"]
}

401 Unauthorized
{ "error": "unauthorized" }
```

## Python FastAPI Integration

Add this middleware to each protected FastAPI app. Remove the app's existing authentication.

**`auth_middleware.py`** — drop this file into the protected app's project root:

```python
import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

AUTH_APP_URL = "https://auth.mainpage.com"
VERIFY_TOKEN_URL = f"{AUTH_APP_URL}/api/verify-token"
THIS_APP_NAME = "budget-site"  # Change to this app's identifier


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth check for health and static assets
        if request.url.path in ("/health", "/favicon.ico") or request.url.path.startswith("/static"):
            return await call_next(request)

        token = request.cookies.get("auth_token")
        if not token:
            return _redirect_to_login(request)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    VERIFY_TOKEN_URL,
                    cookies={"auth_token": token},
                )
        except httpx.RequestError:
            # auth-app unreachable — deny access rather than fail open
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"error": "authentication_service_unavailable"},
                status_code=503,
            )

        if response.status_code != 200:
            return _redirect_to_login(request)

        user = response.json()

        # Enforce per-app access
        if THIS_APP_NAME not in user.get("apps", []):
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "forbidden"}, status_code=403)

        # Attach user info for downstream handlers
        request.state.user = user
        return await call_next(request)


def _redirect_to_login(request: Request) -> RedirectResponse:
    original_url = str(request.url)
    return RedirectResponse(
        f"{AUTH_APP_URL}/login?redirect={original_url}",
        status_code=302,
    )
```

**Register the middleware in `main.py`**:

```python
from fastapi import FastAPI
from auth_middleware import AuthMiddleware

app = FastAPI()
app.add_middleware(AuthMiddleware)
```

**Access the authenticated user in route handlers**:

```python
from fastapi import Request

@app.get("/dashboard")
async def dashboard(request: Request):
    user = request.state.user  # dict: user_id, username, role, apps
    return {"message": f"Hello, {user['username']}"}
```

## React / Next.js Integration

Add a `useAuth` hook that checks authentication before rendering any page.

**`src/hooks/useAuth.js`**:

```javascript
import { useEffect, useState } from "react";

const AUTH_APP_URL = "https://auth.mainpage.com";
const THIS_APP_NAME = "budget-site"; // Change to this app's identifier

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${AUTH_APP_URL}/api/verify-token`, {
      credentials: "include",
    })
      .then((res) => {
        if (res.status === 401) {
          window.location.href = `${AUTH_APP_URL}/login?redirect=${encodeURIComponent(window.location.href)}`;
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (!data) return;
        if (!data.apps?.includes(THIS_APP_NAME)) {
          // User authenticated but not permitted for this app
          window.location.href = `${AUTH_APP_URL}/login?error=forbidden`;
          return;
        }
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        // auth-app unreachable — show error, do not fail open
        setLoading(false);
      });
  }, []);

  return { user, loading };
}
```

**Usage in a page component**:

```javascript
import { useAuth } from "../hooks/useAuth";

export default function DashboardPage() {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading…</div>;
  if (!user) return null; // redirect already in progress

  return <div>Hello, {user.username}</div>;
}
```

## Nginx Configuration

See [`docs/nginx/auth.mainpage.com.conf`](nginx/auth.mainpage.com.conf) for the auth-app Nginx block.

For each protected application, add the `proxy_cookie_domain` directive so the shared
`.mainpage.com` cookie is forwarded across subdomains:

```nginx
# In the protected app's server block (web-folders nginx config)
location / {
    proxy_pass http://budget-site:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # Required: rewrite Set-Cookie domain so the auth_token cookie
    # issued by auth.mainpage.com is sent to *.mainpage.com subdomains
    proxy_cookie_domain auth.mainpage.com .mainpage.com;
}
```

## Migration Checklist for Each Protected Application

1. Remove the application's existing login page, session management, and auth routes.
2. Copy `auth_middleware.py` (or equivalent hook) into the project.
3. Set `THIS_APP_NAME` to the application's identifier (see list below).
4. Register the middleware before any route that requires authentication.
5. Add `proxy_cookie_domain auth.mainpage.com .mainpage.com;` to the Nginx server block.
6. Request the admin to enable this app for the relevant users in auth-app's admin panel.
7. Smoke test: clear cookies → navigate to app → verify redirect → log in → verify return.

## Protected Application Identifiers

| Application | `app_name` identifier |
|---|---|
| Budget Site | `budget-site` |
| Family Admin Routine | `family-admin-routine` |
| Family Archive | `family-archive` |
| Family Kitchen Recipes | `family-kitchen-recipes` |
| New Site | `new-site` |
| Portuguese Expenses | `portuguese-expenses` |
| Reminders App | `reminders-app` |
| Servinga Dashboard | `servinga-dashboard` |

## Security Notes

- The `auth_token` cookie is `httpOnly`, `Secure`, and `SameSite=Lax`. JavaScript on protected
  apps cannot read it; it is forwarded automatically by the browser.
- Never allow a `401` from the verify endpoint to silently grant access. Always redirect or deny.
- If auth-app is unreachable, return `503` rather than failing open. Users will retry after the
  outage is resolved.
- The `apps` list in the verify response reflects the state at token-verification time. An admin
  disabling access takes effect on the user's next request after their token's `last_used_at` is
  refreshed (immediate enforcement requires token invalidation — the admin panel does this via the
  block + unblock flow if instant enforcement is needed).
