# Security Review: auth-app SECURITY-CRITICAL Tasks

**Date**: 2026-05-31
**Reviewer**: security-architect
**Files Reviewed**:
- `backend/services/token_service.py` (T022)
- `backend/services/auth_service.py` (T023)
- `backend/routers/verify.py` (T030)
- `backend/dependencies.py` (T031)
- `backend/services/oauth_service.py` (T036, T037)
- `backend/routers/auth.py` (T038)

---

**FINAL STATUS: ALL TASKS APPROVED** (post-fix re-review 2026-05-31)

## Summary Decision per Task

| Task | File | Decision |
|---|---|---|
| T022 | token_service.py | **APPROVED** |
| T023 | auth_service.py | **APPROVED** (SA-001 fixed: dummy bcrypt added) |
| T030 | routers/verify.py | **APPROVED** |
| T031 | dependencies.py | **APPROVED** |
| T036 | oauth_service.py (Google) | **APPROVED** |
| T037 | oauth_service.py (GitHub) | **APPROVED** |
| T038 | routers/auth.py (OAuth router) | **APPROVED** (SA-003 fixed: CSRF nonce added) |

---

## T022 — TokenService — APPROVED

### Verified Controls

- [x] `secrets.token_hex(32)` used — produces exactly 64-character hex string (256-bit entropy)
- [x] `validate_token()` checks all three: token exists, `expires_at <= _now()`, `user.is_active == True`
- [x] Expired tokens are deleted eagerly on detection (`await token_repo.delete(token)`)
- [x] `last_used_at` updated only on successful validation path
- [x] Token value never appears in any log statement
- [x] `cleanup_expired()` deletes only rows where `expires_at < NOW()` via `delete_expired(_now())`
- [x] `_now()` uses `datetime.now(timezone.utc)` — avoids deprecated `utcnow()`
- [x] Consistent naive-UTC datetimes throughout (`.replace(tzinfo=None)`) — comparison is coherent

### Notes

The `delete(token)` in the expiry path has no explicit `await db.commit()` — it relies on session lifecycle management. Security impact: none (expired token still returns None correctly). The hourly cleanup handles the deletion. Confirmed acceptable.

---

## T023 — AuthService.login() — APPROVED WITH RISKS

### Verified Controls

- [x] `CryptContext` is module-level — not instantiated per call (correct after code-reviewer fix)
- [x] `is_active` check is performed AFTER bcrypt verification (preserves timing normalization for blocked-user path)
- [x] `password` argument is never logged at any log level
- [x] `password_hash` is never logged at any log level
- [x] `auth_logs` records method, IP, success/failure reason separately from HTTP response
- [x] Token value returned from `generate_token()` — never logged or included in error response
- [x] HTTP response is identical (`invalid_credentials` / 401) for wrong-password and user-not-found paths
- [x] IP extracted from `X-Real-IP` or `X-Forwarded-For` header

### Finding: SA-001 — Medium — Timing Normalization Gap

**Location**: `auth_service.py` lines 34–45

When `user is None or user.password_hash is None`, the code returns immediately without calling `_pwd_ctx.verify()`. An attacker can measure response time to distinguish "username does not exist" (fast) from "wrong password" (slow, bcrypt cost).

**Recommended fix**:
```python
_DUMMY_HASH = _pwd_ctx.hash("dummy_value_never_used_0x99")

# When user not found, still run bcrypt to normalize timing:
if user is None or user.password_hash is None:
    _pwd_ctx.verify(password, _DUMMY_HASH)  # discard result
    await log_repo.create(AuthLog(..., reason="invalid_credentials"))
    await db.commit()
    return None, "invalid_credentials"
```

**Risk acceptance**: This is a private family system with ~10 known users. Username enumeration risk is low. No rate limiting already accepted by Product Manager per spec. **Accepted residual risk with recommendation to fix in next iteration.** Phase 3 checkpoint is NOT blocked by this finding.

### Finding: SA-002 — Informational — Blocked User Response Differentiation

The login router returns `403` for blocked users vs `401` for invalid credentials. An attacker who already knows the correct credentials can learn whether their account is blocked. Impact is negligible (requires already knowing the password). Flagged for awareness only.

---

## T030 — Verify-token Router — APPROVED

### Verified Controls

- [x] Token read from `Cookie: auth_token` first, falls back to `Authorization: Bearer`
- [x] All failure paths (no token, invalid token, expired, blocked user) return identical `{"error": "unauthorized"}` with HTTP 401
- [x] Success response contains only `user_id`, `username`, `role`, `apps`
- [x] `apps` list uses `.is_(True)` — only `is_enabled=True` entries returned
- [x] Raw token value never included in any response path
- [x] `last_used_at` updated only via `validate_token()` success path (before returning user)

### Notes

FastAPI's `HTTPException(detail={"error": "unauthorized"})` returns the body as `{"detail": {"error": "unauthorized"}}`. The spec says `{"error": "unauthorized"}`. This is a spec compliance discrepancy — not a security issue. Code reviewer should address if strict spec compliance is required.

---

## T031 — require_auth / require_admin Dependencies — APPROVED

### Verified Controls

- [x] `require_auth` returns HTTP 401 (not 403) for all token failures
- [x] `require_auth` delegates to `TokenService.validate_token()` which validates both token validity AND `user.is_active`
- [x] Injected as FastAPI `Depends()` — clean DI pattern, enforced at framework level
- [x] Handles both cookie and Bearer token extraction identically to verify router
- [x] `require_admin` chains `Depends(require_auth)` — no bypass possible
- [x] Admin role check: `current_user.role != "admin"` → 403 — server-side enforcement

---

## T036 — GoogleOAuthProvider — APPROVED

### Verified Controls

- [x] `get_authorization_url(state)` accepts state as parameter — correct interface (CSRF nonce responsibility is caller's, i.e. T038)
- [x] `exchange_code()` calls Google token endpoint server-side via HTTPS; `GOOGLE_CLIENT_SECRET` from `settings` (env var) — never sent to frontend
- [x] Scope is `"openid email"` only — no unnecessary permissions requested
- [x] `get_verified_email()` checks `email_verified` flag from Google userinfo response — rejects unverified emails
- [x] Returns `(email, sub)` tuple; returns None if email absent or unverified

---

## T037 — GitHubOAuthProvider — APPROVED

### Verified Controls

- [x] Uses `/user/emails` endpoint — NOT `/user` profile endpoint (which may expose unverified email)
- [x] Filters for `primary=True AND verified=True` — rejects unverified emails
- [x] Returns None if no primary verified email found
- [x] `GITHUB_CLIENT_SECRET` from `settings` (env var) — never sent to frontend
- [x] Requests `user:email` scope — minimal required permission

### Notes

GitHub doesn't expose a stable numeric ID via the emails endpoint; the implementation uses the email itself as the provider identifier. This is acceptable — the email is stable for account linking purposes. `github_id` will store the email string rather than a numeric ID.

---

## T038 — OAuth Router (google_auth, github_auth callbacks) — CHANGES REQUIRED

### Critical Finding: SA-003 — Blocker — OAuth State Contains No CSRF Nonce

**Location**: `routers/auth.py` lines 103–107, 149–152, and callbacks lines 111–146, 156–191

**Current implementation**:
```python
# Initiate OAuth:
state = urllib.parse.quote(redirect) if redirect and _is_safe_redirect(redirect) else ""

# On callback:
redirect_url = urllib.parse.unquote(state) if state else ""
if redirect_url and not _is_safe_redirect(redirect_url):
    redirect_url = ""
```

The `state` parameter only encodes the redirect URL. It does not contain a cryptographically random nonce. There is no server-side storage or validation of a CSRF token bound to the initiating session.

**Attack scenario (OAuth CSRF)**:
1. Attacker logs into their own Google/GitHub account via auth-app's OAuth flow
2. Attacker captures the callback URL: `GET /api/auth/callback/google?code=ATTACKER_CODE&state=...`
3. Attacker tricks a victim's browser into visiting this callback URL (e.g., via an `<img>` src or iframe)
4. auth-app exchanges the attacker's code, retrieves the attacker's email, looks up the attacker's account, issues a session cookie to the victim
5. Victim is now logged in as the attacker

Impact: Session fixation — victim browser is silently logged in as attacker. The attacker then visits resources under the victim's browser session (possible if they share a device or the attacker has additional CSRF vectors).

**Required fix**:

```python
import secrets, json

# In google_auth / github_auth initiation endpoint:
csrf_nonce = secrets.token_urlsafe(32)
state_payload = json.dumps({"nonce": csrf_nonce, "redirect": redirect if _is_safe_redirect(redirect) else ""})
state = urllib.parse.quote(state_payload)
# Store csrf_nonce server-side (signed cookie or short-lived DB record, TTL ~10min)
response = RedirectResponse(url, status_code=302)
response.set_cookie("oauth_state", csrf_nonce, httponly=True, secure=is_prod, samesite="lax", max_age=600)
return response

# In callback:
state_payload = json.loads(urllib.parse.unquote(state)) if state else {}
received_nonce = state_payload.get("nonce", "")
stored_nonce = request.cookies.get("oauth_state", "")
if not received_nonce or not stored_nonce or not secrets.compare_digest(received_nonce, stored_nonce):
    return RedirectResponse(f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302)
# Clear the nonce cookie
# Proceed with code exchange
```

**Why this blocks release**: OAuth CSRF is a well-documented, practically exploitable vulnerability in OAuth implementations. The OAuth 2.0 spec (RFC 6749 §10.12) mandates state parameter use as CSRF protection. This must be fixed before production deployment.

### Secondary Finding: SA-004 — Low — HTTP Redirect URLs Allowed

**Location**: `_is_safe_redirect()` line 24

`parsed.scheme in ("http", "https")` allows HTTP redirect targets. In production all `.mainpage.com` apps should be HTTPS. HTTP redirect targets could allow a downgrade if a subdomain is misconfigured. Recommend restricting to `"https"` only in production (`ENVIRONMENT == "production"` check).

---

## Required Actions Before Phase 6 Sign-Off

### Blocker (must fix)

**SA-003**: Backend must add CSRF nonce to OAuth state parameter.

Suggested implementation approach for backend agent:
1. Add `oauth_state` cookie generation in `google_auth` and `github_auth` endpoints using `secrets.token_urlsafe(32)`
2. Encode nonce + redirect URL into state as JSON, URL-encode the whole payload
3. On callback: decode state, extract nonce, compare with `oauth_state` cookie using `secrets.compare_digest()`, clear cookie
4. Reject callback with redirect to `/login?error=forbidden` if nonce is absent, mismatched, or cookie is missing

### Non-blocking (track)

**SA-001** (Medium): Add dummy bcrypt to `auth_service.py` login to normalize timing for user-not-found case. Accepted residual risk for Phase 3; should be addressed before production.

**SA-004** (Low): Restrict redirect URL scheme to `https` in production environment in `_is_safe_redirect()`.

---

## Phase Gate Status (Final)

| Phase | Security Status | Notes |
|---|---|---|
| Phase 3 (Password Login) | **APPROVED** | T022, T023, T031 cleared. SA-001 resolved (dummy bcrypt added). |
| Phase 4 (Token Verify) | **APPROVED** | T030, T031 cleared. |
| Phase 5 (Redirect Flow) | **APPROVED** | Redirect validation in `_is_safe_redirect()` correct. |
| Phase 6 (OAuth Login) | **APPROVED** | SA-003 resolved: `_create_oauth_state()`/`_consume_oauth_state()` with `secrets.token_urlsafe(32)` nonce, server-side store, single-use pop() on callback. |
| Phase 7 (Admin Panel) | **APPROVED** | Admin endpoints use `require_admin` dependency — server-side enforced. |

**ALL phases cleared for merge.**

---

## Residual Risks Accepted

| ID | Finding | Severity | Status | Accepted By | Due |
|---|---|---|---|---|---|
| SA-001 | Login timing normalization gap | Medium | **RESOLVED** — dummy bcrypt added | — | — |
| SA-002 | 403 vs 401 for blocked user login (minor status disclosure) | Informational | Open | — | Optional |
| SA-003 | OAuth state missing CSRF nonce | Blocker | **RESOLVED** — server-side nonce store added | — | — |
| SA-004 | HTTP scheme allowed in `_is_safe_redirect()` | Low | Open — acceptable in dev; ENVIRONMENT=production enforced in CI | DevOps | Before production |
| SA-005 | OAuth CSRF nonce bypass via empty/unknown state | Blocker | **RESOLVED** — both callbacks now reject with 302 when `state` is empty or nonce not in store (auth.py:143-152, 197-206) | — | — |
