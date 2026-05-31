# API Contracts: Centralized Authentication Gateway

Base URL: `https://auth.mainpage.com`

All endpoints are documented via FastAPI OpenAPI at `/docs`.

---

## Public Endpoints (no authentication required)

### POST /api/auth/login

Username/password authentication.

**Request**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200** — token set as `httpOnly` cookie; body:
```json
{
  "message": "ok"
}
```

**Response 401**
```json
{
  "error": "invalid_credentials"
}
```

**Response 403** — user is blocked:
```json
{
  "error": "forbidden"
}
```

**Side effects**:
- Issues `auth_token` cookie: `httpOnly`, `Secure`, `SameSite=lax`,
  `domain=.mainpage.com`, `max-age` = TOKEN_TTL_HOURS × 3600.
- Inserts a row into `auth_logs`.

---

### GET /api/auth/google

Redirects the browser to Google's OAuth2 authorization URL with the
configured `GOOGLE_CLIENT_ID`, `scope=openid email`, and
`redirect_uri=GOOGLE_REDIRECT_URI`.

**Response 302** → Google authorization page

---

### GET /api/auth/callback/google

Handles the OAuth2 authorization code callback from Google.

**Query parameters**: `code`, `state`

**Response 302** → redirect to original application URL (from `state`) on
success, or to `/login?error=forbidden` on 403.

**Response 403** — email not found in users table:
```json
{
  "error": "forbidden"
}
```

**Side effects**: Issues `auth_token` cookie; inserts a row into `auth_logs`;
updates `google_id` on the user row if not already set.

---

### GET /api/auth/github

Redirects the browser to GitHub's OAuth2 authorization URL.

**Response 302** → GitHub authorization page

---

### GET /api/auth/callback/github

Handles the OAuth2 authorization code callback from GitHub.

**Query parameters**: `code`, `state`

**Response 302** → redirect to original application URL on success, or
`/login?error=forbidden` on 403.

**Response 403** — email not found in users table:
```json
{
  "error": "forbidden"
}
```

**Side effects**: Issues `auth_token` cookie; inserts a row into `auth_logs`;
updates `github_id` on the user row if not already set.

---

## Token Endpoints (any authenticated request)

### POST /api/auth/logout

Invalidates the current session token.

**Cookie required**: `auth_token`

**Response 200**:
```json
{
  "message": "ok"
}
```

**Side effects**: Deletes the `auth_tokens` row for the presented token;
clears the `auth_token` cookie.

---

### GET /api/verify-token

Verifies a token and returns the user's identity and permitted applications.
This is the primary integration endpoint consumed by protected applications.

**Token source** (in priority order):
1. Cookie: `auth_token`
2. Header: `Authorization: Bearer <token>`

**Response 200** — valid token:
```json
{
  "user_id": "uuid-string",
  "username": "string",
  "role": "user",
  "apps": ["budget-site", "family-archive"]
}
```

`role` is `"admin"` or `"user"`.
`apps` contains only application names where `user_app_access.is_enabled = TRUE`.

**Response 401** — missing, expired, or invalid token:
```json
{
  "error": "unauthorized"
}
```

**Response 403** — token valid but user is blocked:
```json
{
  "error": "forbidden"
}
```

**Side effects**: Updates `auth_tokens.last_used_at` on successful verification.

---

## Admin Endpoints (role = admin required)

All admin endpoints require a valid `auth_token` cookie belonging to a user
with `role = 'admin'`. Non-admin requests receive `403`.

### GET /api/admin/users

Returns the full user list.

**Response 200**:
```json
[
  {
    "id": "uuid",
    "username": "string",
    "email": "string or null",
    "role": "admin|user",
    "is_active": true,
    "created_at": "2026-05-31T00:00:00Z"
  }
]
```

---

### POST /api/admin/users

Creates a new user.

**Request**:
```json
{
  "username": "string",
  "email": "string or null",
  "password": "string",
  "role": "user"
}
```

`role` must be `"user"` (admins cannot create other admins via this endpoint).
`password` is bcrypt-hashed before storage; the plaintext value is not logged.

**Response 201**:
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string or null",
  "role": "user",
  "is_active": true,
  "created_at": "2026-05-31T00:00:00Z"
}
```

**Response 409** — username or email already exists:
```json
{
  "error": "conflict",
  "detail": "username already exists"
}
```

**Side effects**: Creates `UserAppAccess` rows for all 8 apps with
`is_enabled = FALSE`.

---

### PATCH /api/admin/users/{user_id}

Updates a user's `is_active` status (block/unblock).

**Path parameter**: `user_id` (UUID)

**Request**:
```json
{
  "is_active": false
}
```

**Response 200**:
```json
{
  "id": "uuid",
  "username": "string",
  "is_active": false
}
```

**Response 404** — user not found:
```json
{
  "error": "not_found"
}
```

**Side effects**: When `is_active` is set to `false`, all `auth_tokens` rows
for this user are deleted within the same database transaction.

---

### GET /api/admin/users/{user_id}/apps

Returns the app access configuration for a user.

**Response 200**:
```json
[
  { "app_name": "budget-site",           "is_enabled": true  },
  { "app_name": "family-admin-routine",  "is_enabled": false },
  { "app_name": "family-archive",        "is_enabled": true  },
  { "app_name": "family-kitchen-recipes","is_enabled": false },
  { "app_name": "new-site",              "is_enabled": false },
  { "app_name": "portuguese-expenses",   "is_enabled": false },
  { "app_name": "reminders-app",         "is_enabled": false },
  { "app_name": "servinga-dashboard",    "is_enabled": false }
]
```

---

### PUT /api/admin/users/{user_id}/apps

Replaces all app access flags for a user.

**Request**:
```json
[
  { "app_name": "budget-site",           "is_enabled": true  },
  { "app_name": "family-admin-routine",  "is_enabled": false },
  { "app_name": "family-archive",        "is_enabled": true  },
  { "app_name": "family-kitchen-recipes","is_enabled": false },
  { "app_name": "new-site",              "is_enabled": false },
  { "app_name": "portuguese-expenses",   "is_enabled": false },
  { "app_name": "reminders-app",         "is_enabled": false },
  { "app_name": "servinga-dashboard",    "is_enabled": false }
]
```

All 8 application entries must be present. Unknown `app_name` values are
rejected with `422`.

**Response 200**: Same structure as GET response above.

---

## Health Check

### GET /health

**Response 200** (always, if the service is running):
```json
{
  "status": "ok"
}
```

No authentication required. Used by CI/CD pipeline post-deploy health check.

---

## Error Response Shape (consistent across all endpoints)

```json
{
  "error": "snake_case_error_code",
  "detail": "Optional human-readable description"
}
```

HTTP status codes used:
- `200` OK
- `201` Created
- `302` Redirect (OAuth flows)
- `401` Unauthorized (no/expired/invalid token)
- `403` Forbidden (blocked user, insufficient role, unknown OAuth email)
- `404` Not Found
- `409` Conflict (duplicate username/email)
- `422` Unprocessable Entity (validation error, FastAPI default)
