# Threat Model: auth-app — Centralized Authentication Gateway

**Scope**: auth-app as a public-facing authentication gateway for 8 private family web applications.
**Date**: 2026-05-31
**Method**: STRIDE + Abuse Cases

---

## Scope

auth-app is the single authentication entry point for 8 protected family applications hosted on subdomains of `.mainpage.com`. It handles:
- Username/password login (bcrypt)
- Google OAuth2 and GitHub OAuth2 authorization code flows
- Opaque session token issuance and verification (64-char hex, stored in PostgreSQL)
- httpOnly cookie delivery (`auth_token`, `SameSite=Lax`, `Secure`, domain `.mainpage.com`)
- Admin user management (create, block/unblock users; manage per-user app access)
- Token verification endpoint consumed by all 8 protected apps

---

## Assets

| Asset | Sensitivity | Notes |
|---|---|---|
| User passwords (bcrypt hash) | High | Compromise enables offline cracking |
| Plaintext passwords in transit | Critical | Must never be logged or persisted |
| Session tokens (`auth_token`) | High | Bearer credential; full session access |
| OAuth authorization codes | High | Short-lived but critical; replay = account takeover |
| OAuth state parameter | High | CSRF protection mechanism |
| Google/GitHub client secrets | Critical | Compromise enables token forgery |
| `SECRET_KEY` | Critical | App secret; compromise undermines integrity |
| `DATABASE_URL` | Critical | Full DB access |
| User PII (email, username) | Medium | Private family system |
| `auth_logs` audit trail | Medium | Tamper enables denial of security events |
| Admin panel access | High | User management and app access control |
| `user_app_access` table | High | Controls which apps each user can reach |

---

## Actors

| Actor | Trust Level | Notes |
|---|---|---|
| Authenticated user (valid token) | Low | Verified identity; access limited to permitted apps |
| Admin user | Medium | Elevated trust; can manage users and access |
| Unauthenticated visitor | Untrusted | No assumed identity |
| Protected app backend (verify-token caller) | Medium | Internal; must be on `.mainpage.com` |
| Google OAuth provider | Medium | External; responses must be validated |
| GitHub OAuth provider | Medium | External; responses must be validated |
| Network attacker (MITM, eavesdropper) | Malicious | Mitigated by HTTPS + Secure cookie |
| Brute-force attacker | Malicious | Automated credential stuffing |
| CSRF attacker | Malicious | Cross-origin form submission / OAuth state forgery |
| Insider / compromised admin | Malicious | Admin can block users; cannot delete |

---

## Trust Boundaries

1. **Public internet → auth-app** (login endpoints, OAuth redirects)
2. **auth-app → Google/GitHub** (OAuth token exchange, userinfo calls)
3. **auth-app → PostgreSQL** (all data persistence; shared `web-folders` instance)
4. **Protected app → auth-app** (GET /api/verify-token via internal network)
5. **Browser → auth-app frontend** (React SPA; cookie scoped to `.mainpage.com`)
6. **auth-app admin endpoints** (require_admin dependency enforces elevated trust)

---

## Data Flows

```
[Browser] ──POST /api/auth/login─────────────────→ [auth-app backend]
                                                        ↓ bcrypt.verify
                                                     [PostgreSQL users]
                                                        ↓ secrets.token_hex(32)
                                                     [PostgreSQL auth_tokens]
          ←──Set-Cookie: auth_token (httpOnly)────────
          
[Browser] ──GET /api/auth/google──────────────────→ [auth-app] → redirect → [Google]
[Browser] ──GET /api/auth/callback/google?code&state → [auth-app]
                                                        ↓ exchange_code (server-side)
                                                     [Google token endpoint]
                                                        ↓ get_verified_email
                                                     [Google userinfo endpoint]
                                                        ↓ lookup by email
                                                     [PostgreSQL users]

[Protected app] ──GET /api/verify-token──────────→ [auth-app]
                                                        ↓ token lookup
                                                     [PostgreSQL auth_tokens + user_app_access]
              ←──{ user_id, username, role, apps }──
```

---

## Entry Points

| Entry Point | Protocol | Auth Required | Risk |
|---|---|---|---|
| `POST /api/auth/login` | HTTPS | No | Credential brute-force, enumeration |
| `GET /api/auth/google` | HTTPS | No | Open redirect, CSRF |
| `GET /api/auth/callback/google` | HTTPS | No (state validates) | Code injection, state replay |
| `GET /api/auth/github` | HTTPS | No | Same as Google |
| `GET /api/auth/callback/github` | HTTPS | No (state validates) | Same as Google |
| `POST /api/auth/logout` | HTTPS | Cookie | CSRF (low risk; logout is safe) |
| `GET /api/verify-token` | HTTPS | Cookie/Bearer | Enumeration, timing attacks |
| `GET /api/admin/users` | HTTPS | Admin cookie | Privilege escalation |
| `POST /api/admin/users` | HTTPS | Admin cookie | Privilege escalation |
| `PATCH /api/admin/users/{id}` | HTTPS | Admin cookie | Privilege escalation |
| `GET/PUT /api/admin/users/{id}/apps` | HTTPS | Admin cookie | Privilege escalation |
| `GET /health` | HTTPS | No | Info disclosure (minimal) |
| `GET /docs` | HTTPS | No | API schema disclosure |

---

## Threats and Abuse Cases

### T1 — Spoofing: Credential Stuffing / Brute Force on Login
- **Impact**: Account takeover
- **Likelihood**: Medium (private family system, known users, but endpoint is public)
- **Controls**: bcrypt cost factor slows verification; all failures logged to `auth_logs`; no lockout (accepted risk per spec)
- **Residual Risk**: No rate limiting; attacker with password list can attempt indefinitely
- **Mitigation required**: Log all failures with IP; consider adding rate limiting in future

### T2 — Spoofing: OAuth State Parameter Forgery (CSRF)
- **Impact**: Attacker-controlled session in victim's browser (OAuth CSRF)
- **Likelihood**: Medium (if state not validated)
- **Controls**: `state` parameter must be cryptographically random, bound to session, validated on callback; server rejects callback if state mismatches
- **Residual Risk**: None if implemented correctly
- **Mitigation required (T038)**: `state` must be generated with `secrets.token_urlsafe()`, stored server-side or signed, and validated before processing the OAuth code

### T3 — Spoofing: OAuth Email Spoofing / Unverified Email
- **Impact**: Account takeover if attacker controls email associated with victim's Google/GitHub
- **Likelihood**: Low (provider verifies email)
- **Controls**: Only primary *verified* email used; GitHub `/user/emails` endpoint required (not `/user` profile); unknown emails denied
- **Residual Risk**: If provider allows unverified email claim (GitHub edge case)
- **Mitigation required (T037)**: MUST call `/user/emails`, filter `primary=true AND verified=true`, NOT use profile email

### T4 — Tampering: Token Forgery
- **Impact**: Arbitrary session as any user
- **Likelihood**: Very Low (64-char random opaque token; 2^256 space)
- **Controls**: `secrets.token_hex(32)` — cryptographically secure; stored in DB; validated on every request
- **Residual Risk**: Negligible if token generation is correct

### T5 — Tampering: Token Value Exposed in Logs/Responses
- **Impact**: Token theft → session hijack
- **Likelihood**: Medium if not controlled
- **Controls**: Token delivered only as httpOnly cookie; response body must never include raw token; logging must never log token values
- **Residual Risk**: None if T022/T025 follow the rule
- **Mitigation required (T022, T025)**: Token value must never appear in: JSON response bodies, error messages, log lines, HTTP headers other than Set-Cookie

### T6 — Tampering: SQL Injection
- **Impact**: Data exfiltration, authentication bypass
- **Likelihood**: Very Low (SQLAlchemy ORM only; parameterized queries)
- **Controls**: All DB access through SQLAlchemy ORM (plan requirement); no raw SQL
- **Residual Risk**: Negligible if ORM-only rule is followed

### T7 — Repudiation: Auth Log Tampering
- **Impact**: Denial of security events; evidence destruction
- **Likelihood**: Low (internal threat)
- **Controls**: `auth_logs` is INSERT-only by design; no UPDATE/DELETE in `LogRepository`
- **Residual Risk**: Logs not shipped to external SIEM; single DB instance
- **Mitigation required (T059)**: Verify `LogRepository` has no UPDATE/DELETE methods

### T8 — Information Disclosure: Username Enumeration via Login Response
- **Impact**: Attacker learns valid usernames
- **Likelihood**: High (generic implementation risk)
- **Controls**: Login failure response must be identical for "wrong password" and "user not found"; timing must be constant (bcrypt verify even for non-existent users)
- **Mitigation required (T023)**: When user not found, still run a dummy bcrypt.checkpw() to normalize timing

### T8b — Information Disclosure: Verify-Token Enumeration
- **Impact**: Attacker probes token space; timing attack reveals valid vs. invalid tokens
- **Likelihood**: Low (64-char token space)
- **Controls**: Response must be identical 401 for all failure modes; constant-time comparison for token lookup (ORM lookup by value is fine; DB index makes this fast for all cases)
- **Mitigation required (T030)**: All failure paths return identical `{"error": "unauthorized"}` 401; no field in response leaks failure mode

### T9 — Information Disclosure: Secret Exposure
- **Impact**: Full system compromise
- **Likelihood**: Medium (common developer mistake)
- **Controls**: All secrets via `.env` only; pydantic-settings reads from env; never hardcoded; never logged
- **Mitigation required (T007, T015)**: `config.py` must use `pydantic-settings`; no secret default values in `Settings` class; error messages must not echo config values

### T10 — Denial of Service: Token Table Flooding
- **Impact**: Database bloat; slow token validation queries
- **Likelihood**: Low (private system; limited attacker surface)
- **Controls**: Hourly cleanup via APScheduler (T024); expired tokens removed regularly
- **Residual Risk**: Between cleanup cycles, table can accumulate; mitigated by index on `token_value`

### T11 — Elevation of Privilege: Admin Endpoint Bypass
- **Impact**: Non-admin creates/blocks users; manages app access
- **Likelihood**: Medium (if authorization only enforced client-side)
- **Controls**: `require_admin` FastAPI dependency on ALL admin router endpoints; server-side role check; no client-side-only enforcement
- **Mitigation required (T042)**: Every admin endpoint must declare `require_admin` as a dependency; verify via integration tests (T062)

### T12 — Elevation of Privilege: Role Self-Promotion
- **Impact**: User promotes own role to admin
- **Likelihood**: Low (if schema is strict)
- **Controls**: Role not accepted from client in `UserCreate` or `PATCH` payload; role can only be set by admin-initiated user creation; `UserCreate` schema must not accept `role` from POST body for non-admins
- **Mitigation required (T041, T042)**: `POST /api/admin/users` must force `role='user'` unless admin explicitly sets it; no endpoint allows a user to update their own role

### T13 — Elevation of Privilege: Open Redirect
- **Impact**: Phishing via crafted login redirect URL
- **Likelihood**: Medium (redirect parameter in login and OAuth state)
- **Controls**: `redirect` URL validated to only accept `.mainpage.com` URLs before issuing redirect; OAuth state carries redirect URL — must validate on callback
- **Mitigation required (T033, T038)**: Strict allowlist check: URL must be `https://*.mainpage.com/...`; reject absolute URLs to other domains; reject protocol-relative URLs

### T14 — CORS Misconfiguration
- **Impact**: Cross-origin requests from attacker-controlled domains access authenticated endpoints
- **Likelihood**: Low if CORS is configured correctly
- **Controls**: `ALLOWED_ORIGINS` from env; must be `*.mainpage.com` subdomains only; no wildcard `*`
- **Mitigation required (T015)**: CORSMiddleware must use explicit origin list; validate `ALLOWED_ORIGINS` does not contain `*`

### T15 — Cookie Security Misconfiguration
- **Impact**: Token theft via XSS or non-HTTPS transmission
- **Likelihood**: Low if cookie flags are set correctly
- **Controls**: `HttpOnly`, `Secure`, `SameSite=Lax`, domain=`.mainpage.com` from `COOKIE_DOMAIN` env var; `max_age` from `TOKEN_TTL_HOURS`
- **Mitigation required (T025)**: All five attributes must be set on every `Set-Cookie`; never omit even on error paths; `COOKIE_DOMAIN` must come from env, not hardcoded

### T16 — Spoofing: Blocked User Token Replay
- **Impact**: Blocked user retains session access until token naturally expires
- **Likelihood**: High if not handled
- **Controls**: Blocking a user MUST call `TokenRepository.delete_by_user_id()` in same transaction as setting `is_active=False`; `validate_token()` also checks `is_active` on user
- **Mitigation required (T031, T041)**: Both controls needed (token deletion + active check) for defense in depth; test with T061 integration test

### T17 — OAuth Code Replay
- **Impact**: Attacker intercepts authorization code and replays it
- **Likelihood**: Low (codes are single-use at provider)
- **Controls**: Code exchange happens server-side only; state parameter prevents CSRF; provider enforces single-use
- **Residual Risk**: Very low; provider-enforced

### T18 — GitHub Profile Email Unverified (T037-specific)
- **Impact**: OAuth login with email not owned by user
- **Likelihood**: Medium (GitHub allows unverified emails in profile)
- **Controls**: MUST use `/user/emails` endpoint with `verified=true` filter, NOT `/user.email` field
- **Mitigation required (T037)**: Explicitly call `/user/emails`, filter `primary=true AND verified=true`

---

## Required Mitigations by Task

### T022 — TokenService
- [ ] Use `secrets.token_hex(32)` (produces 64-char hex); never `uuid4()`, `random`, or other PRNG
- [ ] `validate_token()` checks both token existence AND user `is_active`; returns None on either failure
- [ ] Token value must never appear in log output at any log level
- [ ] `cleanup_expired()` uses `expires_at < NOW()` comparison; must not delete active tokens

### T023 — AuthService (password)
- [ ] If user not found, run a dummy `bcrypt.checkpw()` call to normalize timing (anti-enumeration)
- [ ] Never log plaintext password at any level; never log password_hash
- [ ] Failure reason in `auth_logs` must be `'invalid_password'` or `'user_not_found'` (generic); not `'user_blocked'` distinguishing message that leaks status
- [ ] Actually, `'user_blocked'` IS acceptable in logs — it's the internal audit record, not the user-facing error; user-facing error must be generic ("invalid credentials")
- [ ] `is_active` check must be performed AFTER bcrypt verification to prevent user existence enumeration

### T030 — Verify-token router
- [ ] Read token from `Cookie: auth_token` first; fall back to `Authorization: Bearer` header
- [ ] All failure paths (missing token, expired, blocked user, not found) return identical `{"error": "unauthorized"}` 401 — no distinguishing information
- [ ] Update `last_used_at` only on success (not on failure)
- [ ] Apps list must only include `is_enabled=TRUE` entries — never expose disabled apps
- [ ] Never include raw token value in response

### T031 — require_auth dependency
- [ ] Must return 401 (not 403) for all token failures (including blocked user)
- [ ] Must check `is_active` on user retrieved via token — not just token validity
- [ ] Token lookup must use constant-time-equivalent DB lookup (index on token_value)

### T036 — GoogleOAuthProvider
- [ ] `state` parameter must be cryptographically random (`secrets.token_urlsafe(32)`)
- [ ] `state` must be stored server-side (DB or signed cookie) before redirect; validated on callback
- [ ] Code exchange via HTTPS POST to Google token endpoint only; never expose client_secret to frontend
- [ ] Only use `scope=openid email`; do not request unnecessary scopes
- [ ] Validate `redirect_uri` in token exchange matches the registered URI exactly

### T037 — GitHubOAuthProvider
- [ ] MUST call `/user/emails` (not `/user`), filter `primary=true AND verified=true`
- [ ] `state` same requirements as T036
- [ ] Handle GitHub's case where user has no verified primary email — deny access

### T038 — AuthService.oauth_login + OAuth router
- [ ] `state` parameter carries redirect URL AND CSRF token — both must be validated on callback
- [ ] Redirect URL in state must be validated against `.mainpage.com` allowlist before redirect
- [ ] Unknown email: deny with 403, log failure with `'unknown_oauth_email'` reason — do NOT create account
- [ ] Blocked user: deny with 403, log failure with `'user_blocked'` reason
- [ ] `google_id`/`github_id` update on first OAuth login must be atomic with user lookup
- [ ] OAuth errors (provider failure, invalid code) must redirect to `/login?error=provider_error`, not expose internal error details

---

## Security Tests Required

| Test ID | Description | Covers |
|---|---|---|
| ST-001 | Unknown OAuth email → 403, no account created | T038, FR-005, FR-006 |
| ST-002 | OAuth state mismatch → rejected, no session issued | T036, T037, T038 |
| ST-003 | Expired token → 401 from verify-token | T030 |
| ST-004 | Missing token → 401 from verify-token | T030 |
| ST-005 | Blocked user's valid token → 401 from verify-token | T030, T031 |
| ST-006 | Blocked user → 403 on login attempt | T023 |
| ST-007 | Non-admin → 403 on all admin endpoints | T042 |
| ST-008 | Token replay after logout → 401 | T025 |
| ST-009 | Brute-force attempt logged in auth_logs | T023 |
| ST-010 | CORS rejection for non-.mainpage.com origin | T015 |
| ST-011 | Cookie has HttpOnly + Secure + SameSite=Lax flags | T025 |
| ST-012 | Login response identical for wrong-password vs. unknown-user | T023 |
| ST-013 | Redirect URL validated to .mainpage.com only | T033, T038 |
| ST-014 | GitHub unverified email rejected | T037 |
| ST-015 | Admin cannot be created via POST /api/admin/users by non-admin | T042 |
| ST-016 | User cannot promote own role | T041, T042 |
| ST-017 | Block atomically invalidates all user tokens | T041 |

---

## Residual Risks

| Risk | Severity | Owner | Status |
|---|---|---|---|
| No rate limiting on login | Medium | Product Manager | Accepted (private family system, spec assumption) |
| No account lockout after N failures | Medium | Product Manager | Accepted (per spec) |
| `auth_logs` not shipped to external SIEM | Low | DevOps | Track; add in future |
| `/docs` OpenAPI UI publicly accessible | Low | DevOps | Consider restricting to admin in production |
| Shared PostgreSQL: no row-level isolation from other apps | Low | DevOps | Accepted (shared `web-folders` constraint) |
| No MFA | Low | Product Manager | Accepted (private family system) |

---

## Decision / Status

**THREAT MODEL: COMPLETE** — Controls and mitigations defined for all identified threats.
Security review of T022, T023, T030, T031, T036, T037, T038 will verify controls are implemented.
