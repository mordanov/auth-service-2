# Research: Centralized Authentication Gateway

## Resolved Design Decisions

### 1. Opaque Token vs. JWT

**Decision**: Opaque tokens stored in PostgreSQL.

**Rationale**: Opaque tokens are immediately revocable by deleting the database
row. JWT-based approaches require a token blocklist to achieve the same
guarantees — which effectively recreates a database lookup on every request.
Since the constitution mandates immediate revocation when a user is blocked,
opaque tokens are the simpler and safer choice. The performance difference is
negligible for a private family system.

**Alternatives considered**:
- JWT with blocklist: more complex, same DB roundtrip cost, no benefit.
- JWT with short TTL (1 min) + refresh: over-engineered for this use case (no
  mobile offline requirements, small user count).

---

### 2. OAuth Flow: Authorization Code vs. Implicit

**Decision**: Authorization Code flow (PKCE not required for server-side flow).

**Rationale**: The backend receives the authorization code and exchanges it for
tokens server-side. The access token from the OAuth provider never touches the
browser. This is the current security best practice; implicit flow is deprecated
in OAuth 2.1. GitHub and Google both support authorization code flow.

**Alternatives considered**:
- Implicit flow: deprecated, token exposed in URL fragment.
- PKCE without client secret: applicable for SPAs; our backend has a client
  secret and performs the exchange server-side, so standard code flow is correct.

---

### 3. Email Matching for OAuth (no auto-registration)

**Decision**: Match OAuth identity by primary verified email only. Return `403`
for unknown emails; create no account.

**Rationale**: The system is a private family gateway; all accounts are
pre-created by admin. OAuth is an identity verifier, not an onboarding path.
Strict email matching prevents accidental account takeover if a provider
allows unverified email claims (GitHub marks emails as verified; Google primary
email is always verified).

**Implementation note**: For GitHub, the `/user/emails` API endpoint must be
called to retrieve the primary verified email (it is not always in the basic
`/user` profile response). `google_id` and `github_id` are stored on the user
row after first successful OAuth login to speed up future lookups.

---

### 4. Background Token Cleanup Strategy

**Decision**: Use FastAPI `startup` event to register a background task via
`asyncio` with a 1-hour sleep loop (or APScheduler with an interval trigger).

**Rationale**: FastAPI built-in `BackgroundTasks` are per-request and
unsuitable for recurring jobs. APScheduler is a mature library that integrates
cleanly with FastAPI's async lifecycle. The KISS principle (constitution §IV)
prefers this over a separate cron container or Celery worker.

**Implementation**: Delete rows from `auth_tokens` where `expires_at < NOW()`
once per hour. The cleanup is best-effort; expired tokens are also rejected
at verification time regardless.

---

### 5. Cookie Domain and SameSite Strategy

**Decision**: `httpOnly=True`, `Secure=True`, `SameSite=lax`,
`domain=".mainpage.com"`.

**Rationale**: `SameSite=lax` allows the cookie to be sent on top-level
navigations (GET redirects) while blocking cross-site POST. This is required
because the auth redirect sends a GET to the protected app, which must carry
the cookie. `SameSite=strict` would strip the cookie on the redirect, breaking
the flow. `domain=.mainpage.com` makes the cookie available to all subdomains,
which is the explicit design goal.

**Alternatives considered**:
- `SameSite=none`: requires `Secure` and is overly permissive for this use
  case; also requires explicit CORS handling on all subdomains.
- `SameSite=strict`: breaks the redirect-back flow after login.

---

### 6. Password Hashing

**Decision**: `bcrypt` with default work factor (12 rounds).

**Rationale**: bcrypt is the mandated algorithm (constitution §VI and
technology stack). Python `passlib[bcrypt]` provides a stable, well-tested
implementation compatible with FastAPI. The default work factor balances
security and login latency for a private system with low concurrent load.

---

### 7. Database Session Management (Async)

**Decision**: `asyncpg` driver + SQLAlchemy 2.x async session factory,
injected via `get_db` FastAPI dependency.

**Rationale**: FastAPI is built on ASGI/asyncio; a synchronous psycopg2
connection would block the event loop. `asyncpg` is the standard async
PostgreSQL driver. SQLAlchemy 2.x provides first-class async support with
`AsyncSession`. Sessions are opened per request and closed in the `finally`
block of the dependency generator, ensuring no connection leaks.

---

### 8. CORS Configuration

**Decision**: Allow origins matching `https://*.mainpage.com`; credentials
allowed; methods: GET, POST, PUT, PATCH, DELETE, OPTIONS.

**Rationale**: Constitution §VI forbids wildcard `*` in production. FastAPI's
`CORSMiddleware` accepts an `allow_origins` list; a regex-based or wildcard
subdomain approach requires careful configuration. The safest approach is an
explicit list derived from the 8 known application hostnames plus
`auth.mainpage.com` itself.

**Implementation note**: The origin list should be read from an
`ALLOWED_ORIGINS` env variable to avoid hardcoding (constitution §VI).

---

### 9. Admin Panel Architecture

**Decision**: Single-page React app served by the same Nginx instance.
Admin routes guarded by a `require_admin` dependency on all backend endpoints
and a React router guard that calls `/api/verify-token` and checks `role`.

**Rationale**: No separate admin service; KISS principle (constitution §IV).
The admin SPA is just another page served under `auth.mainpage.com/admin`.

---

### 10. Alembic Migration Strategy

**Decision**: Alembic `autogenerate` from SQLAlchemy models. `alembic upgrade head`
runs automatically on every deployment (constitution §CI Gate Requirements).
The `db/seed.py` script runs after migrations on first-run (checks if users
table is empty before inserting).

**Rationale**: Alembic is the standard migration tool for SQLAlchemy projects.
Auto-generating from models reduces boilerplate; the seed idempotency check
prevents duplicate seed data on subsequent deployments.
