# Security Acceptance Criteria: auth-app

**Feature**: 001-auth-middleware-app
**Date**: 2026-05-31
**Owner**: security-architect

This document defines the security acceptance criteria for each SECURITY-CRITICAL task.
Implementation agents must satisfy all criteria before requesting merge approval.

---

## T022 — TokenService (`backend/services/token_service.py`)

### Must Pass Before Merge

- [ ] `generate_token()` uses `secrets.token_hex(32)` producing a 64-character hex string
- [ ] No use of `uuid4()`, `random.random()`, `os.urandom()` (directly), or any other PRNG
- [ ] `validate_token()` checks: (a) token exists in DB, (b) `expires_at > NOW()`, (c) `user.is_active == True` — all three; returns None on any failure
- [ ] No token value appears in any log statement at any severity level
- [ ] `cleanup_expired()` deletes only tokens where `expires_at < NOW()`; does not affect unexpired tokens
- [ ] Unit test: `secrets.token_hex(32)` output is exactly 64 hex chars
- [ ] Unit test: `validate_token()` returns None for expired token
- [ ] Unit test: `validate_token()` returns None for blocked user's token
- [ ] Unit test: `cleanup_expired()` leaves valid tokens intact

---

## T023 — AuthService.login() (`backend/services/auth_service.py`)

### Must Pass Before Merge

- [ ] If username not found in DB, still runs `bcrypt.checkpw()` on a dummy hash to normalize timing
- [ ] User-facing error message is identical for "user not found", "wrong password", and "user blocked" — must not distinguish between cases in the HTTP response
- [ ] `password` argument is never logged at any log level
- [ ] `password_hash` is never logged at any log level
- [ ] `is_active` check is performed AFTER bcrypt verification (anti-enumeration)
- [ ] `auth_logs` INSERT records: username as provided, IP from `X-Real-IP` header, method `'password'`, success=True/False, failure reason (internal audit only, not exposed to client)
- [ ] On success: `TokenService.generate_token()` called; login response does not include raw token value
- [ ] Unit test: valid login → token issued, success log entry
- [ ] Unit test: wrong password → None returned, failure log entry, timing comparable to valid-user path
- [ ] Unit test: blocked user → None returned, failure log entry
- [ ] Unit test: nonexistent user → None returned, timing comparable to valid-user path

---

## T030 — Verify-token router (`backend/routers/verify.py`)

### Must Pass Before Merge

- [ ] Reads token from `Cookie: auth_token` first; if absent, reads `Authorization: Bearer <token>`
- [ ] All failure cases return exactly `{"error": "unauthorized"}` with HTTP 401 — no variation
- [ ] Response body never includes the raw token value
- [ ] Success response includes only: `user_id`, `username`, `role`, `apps` (list of enabled app names)
- [ ] `apps` list contains only `is_enabled=True` entries for the user
- [ ] `last_used_at` updated only on successful verification
- [ ] Integration test: valid cookie → 200 with correct fields
- [ ] Integration test: expired token → 401
- [ ] Integration test: no token → 401
- [ ] Integration test: blocked user's valid token → 401
- [ ] Integration test: `apps` only shows enabled entries

---

## T031 — require_auth dependency (`backend/dependencies.py`)

### Must Pass Before Merge

- [ ] Returns HTTP 401 (not 403, not 400) for all token validation failures
- [ ] Validates both token existence/expiry AND `user.is_active`
- [ ] Injected via FastAPI `Depends()` — not inline per-endpoint logic
- [ ] Works for both cookie and Bearer token inputs (delegates to TokenService)

---

## T036 — GoogleOAuthProvider (`backend/services/oauth_service.py`)

### Must Pass Before Merge

- [ ] `get_authorization_url(state)` generates `state` using `secrets.token_urlsafe(32)` minimum
- [ ] `state` is stored server-side before redirect (session, signed cookie, or DB record)
- [ ] `exchange_code(code)` POSTs to Google's token endpoint server-side; `client_secret` never sent to frontend
- [ ] Only scopes `openid email` requested — no profile, no additional scopes
- [ ] `get_verified_email()` returns only the primary verified email from Google userinfo
- [ ] On callback, `state` from request is validated against stored state; mismatch → reject with no session
- [ ] Unit test: state mismatch → rejected
- [ ] Unit test: successful token exchange returns verified email

---

## T037 — GitHubOAuthProvider (`backend/services/oauth_service.py`)

### Must Pass Before Merge

- [ ] `get_verified_email()` calls GitHub `/user/emails` endpoint (NOT `/user`)
- [ ] Filters response to `primary=true AND verified=true`; returns None if no such entry exists
- [ ] If user has no primary verified email, denies access (does not fall back to profile email)
- [ ] Same `state` requirements as T036
- [ ] `exchange_code(code)` is server-side only; `client_secret` never sent to frontend
- [ ] Unit test: GitHub returns unverified primary email → None returned
- [ ] Unit test: GitHub returns no primary email → None returned
- [ ] Unit test: GitHub returns verified primary email → email returned

---

## T038 — AuthService.oauth_login() + OAuth router (`backend/routers/auth.py`, `backend/services/auth_service.py`)

### Must Pass Before Merge

- [ ] `state` parameter carries both CSRF token and redirect URL; both validated on callback
- [ ] Redirect URL extracted from state is validated: must match `https://*.mainpage.com/...` (no other domains; no protocol-relative URLs)
- [ ] Unknown email: HTTP 403, log failure reason `'unknown_oauth_email'`, no account created
- [ ] Blocked user: HTTP 403, log failure reason `'user_blocked'`
- [ ] `google_id`/`github_id` stored/updated on user row after first successful OAuth login
- [ ] OAuth provider errors (bad code, provider down) → redirect to `/login?error=provider_error`; no internal error details in redirect URL or response body
- [ ] No auto-registration under any circumstances — account must pre-exist in `users` table
- [ ] Integration test: known email → 200 + cookie set
- [ ] Integration test: unknown email → 403, no account in DB
- [ ] Integration test: state mismatch → rejected
- [ ] Integration test: blocked user OAuth → 403

---

## Cross-Cutting Security Requirements

These apply to all SECURITY-CRITICAL implementations:

| Requirement | Verification |
|---|---|
| All secrets come from env vars only | `grep -r "client_secret\|client_id\|SECRET_KEY" backend/ --include="*.py"` must show no hardcoded values |
| No raw SQL — ORM only | No `text()`, `execute("SELECT...")`, or raw string interpolation in queries |
| CORS restricted to ALLOWED_ORIGINS | CORSMiddleware configured from env; test with non-mainpage.com origin |
| Passwords never logged | `grep -r "password" backend/ --include="*.py" \| grep -i "log\|print\|debug"` must return nothing |
| httpOnly cookie on every Set-Cookie | Check Set-Cookie header in login response |

---

## Security Review Sign-Off Template

After reviewing each task implementation, the security-architect will record:

```
## Security Review: T0XX — <Name>
Date: YYYY-MM-DD
Reviewer: security-architect
Decision: APPROVED | APPROVED WITH RISKS | CHANGES REQUIRED

### Findings
[List any findings with severity and required action]

### Verified
[List passing criteria]

### Residual Risks
[Any accepted risks with owner and due date]
```
