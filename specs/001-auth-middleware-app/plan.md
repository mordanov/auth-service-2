# Implementation Plan: Centralized Authentication Gateway

**Branch**: `001-auth-middleware-app` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-auth-middleware-app/spec.md`

## Summary

Build `auth-app`, a centralized authentication gateway that serves as the
single sign-on entry point for 8 private family web applications. The service
provides username/password login, Google OAuth2, and GitHub OAuth; issues
opaque session tokens as `httpOnly` cookies; and exposes a `/api/verify-token`
endpoint that protected applications use to validate incoming requests. An
admin panel allows user creation, blocking, and per-application access control.
The backend is Python 3.12 + FastAPI with a strict 4-layer architecture;
the frontend is React + HeroUI with react-i18next (RU/EN).

## Technical Context

**Language/Version**: Python 3.12 (backend); Node.js LTS / React 18 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x + asyncpg, Alembic, passlib[bcrypt], httpx, APScheduler; React + HeroUI + react-i18next + Vitest
**Storage**: PostgreSQL (shared instance from `web-folders`; `asyncpg` async driver)
**Testing**: pytest + pytest-asyncio + pytest-cov (≥80%); Vitest + React Testing Library (≥80%)
**Target Platform**: Linux server (Docker containers); served via shared Nginx
**Project Type**: Web service (full-stack: FastAPI backend + React SPA frontend)
**Performance Goals**: Token verification round-trip < 200ms p95 (single DB lookup)
**Constraints**: Shared PostgreSQL and Nginx — no provisioning of own DB or web server; cookie domain `.mainpage.com`; HTTPS only
**Scale/Scope**: ~10 users, 8 protected applications; private family system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Separation of Concerns | ✅ PASS | 4-layer architecture: Routers→Services→Repositories→Models; React split by pages/components/hooks/api |
| II. Extensibility via Abstraction | ✅ PASS | OAuth providers implement a shared interface; repositories are injectable and mockable; Pydantic schemas separated by concern |
| III. DRY | ✅ PASS | `TokenService` owns all token logic; `require_auth` as single reusable dependency; all UI text in ru.json/en.json |
| IV. KISS | ✅ PASS | FastAPI background tasks / APScheduler for cleanup; docker-compose mirrors budget-site; HeroUI defaults only; no speculative code |
| V. Test-Driven Quality | ✅ PASS | ≥80% backend + frontend coverage enforced in CI; test layout mirrors source layout |
| VI. Security by Default | ✅ PASS | Secrets in .env only; bcrypt; SQLAlchemy ORM only; httpOnly/Secure/SameSite=lax cookies; CORS restricted; non-root Docker user; atomic token revocation on block |

*Post-design re-check*: All principles satisfied by the design in `data-model.md` and `contracts/api.md`. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-auth-middleware-app/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
backend/
├── Dockerfile
├── requirements.txt
├── main.py                    # FastAPI app factory, lifespan, CORS, routers
├── config.py                  # pydantic-settings: all env vars
├── dependencies.py            # get_db, require_auth, require_admin
├── routers/
│   ├── auth.py                # POST /api/auth/login, POST /api/auth/logout,
│   │                          # GET /api/auth/google, GET /api/auth/callback/google,
│   │                          # GET /api/auth/github, GET /api/auth/callback/github
│   ├── verify.py              # GET /api/verify-token
│   └── admin.py               # GET/POST /api/admin/users,
│                              # PATCH /api/admin/users/{id},
│                              # GET/PUT /api/admin/users/{id}/apps
├── services/
│   ├── auth_service.py        # login(), oauth_login(), logout()
│   ├── token_service.py       # generate_token(), validate_token(), cleanup_expired()
│   ├── user_service.py        # create_user(), block_user(), update_app_access()
│   └── oauth_service.py       # GoogleOAuthProvider, GitHubOAuthProvider (shared interface)
├── repositories/
│   ├── user_repository.py     # CRUD on users table
│   ├── token_repository.py    # CRUD on auth_tokens table
│   └── log_repository.py      # INSERT-only on auth_logs table
├── models/
│   ├── user.py                # SQLAlchemy ORM: User, UserAppAccess
│   ├── token.py               # SQLAlchemy ORM: AuthToken
│   └── log.py                 # SQLAlchemy ORM: AuthLog
├── schemas/
│   ├── auth.py                # LoginRequest, LoginResponse, VerifyTokenResponse
│   ├── user.py                # UserCreate, UserResponse, AppAccessItem
│   └── token.py               # TokenCreate (internal)
├── db/
│   ├── database.py            # async engine + AsyncSession factory
│   └── seed.py                # idempotent seed from env vars
├── tasks/
│   └── cleanup.py             # hourly expired-token cleanup (APScheduler)
└── alembic/                   # migrations managed by Alembic

tests/
├── unit/
│   ├── services/
│   │   ├── test_token_service.py
│   │   ├── test_auth_service.py
│   │   ├── test_user_service.py
│   │   └── test_oauth_service.py
│   └── repositories/
│       ├── test_user_repository.py
│       ├── test_token_repository.py
│       └── test_log_repository.py
└── integration/
    └── routers/
        ├── test_auth_router.py
        ├── test_verify_router.py
        └── test_admin_router.py

frontend/
├── Dockerfile
├── package.json
├── vite.config.js
└── src/
    ├── App.jsx                # React Router: / → /login, /admin
    ├── main.jsx               # React + HeroUIProvider + i18n init
    ├── i18n/
    │   ├── index.js           # react-i18next setup
    │   ├── ru.json
    │   └── en.json
    ├── api/
    │   └── authApi.js         # fetch wrappers: login, logout, verifyToken,
    │                          # getUsers, createUser, patchUser, getApps, putApps
    ├── hooks/
    │   └── useAuth.js         # checkAuth() → redirect on 401; return user on 200
    ├── pages/
    │   ├── LoginPage.jsx      # Tabs: password / Google / GitHub; LanguageSwitcher
    │   └── AdminPage.jsx      # UserTable + UserCreateModal + AppAccessCheckboxes
    └── components/
        ├── LoginForm.jsx
        ├── OAuthButtons.jsx
        ├── UserTable.jsx
        ├── UserCreateModal.jsx
        ├── AppAccessCheckboxes.jsx
        └── LanguageSwitcher.jsx

frontend/tests/
├── LoginForm.test.jsx
├── UserTable.test.jsx
├── AppAccessCheckboxes.test.jsx
├── useAuth.test.js
└── LanguageSwitcher.test.jsx

docker-compose.yml             # backend + frontend services; external network to web-folders
.env.example
.github/
└── workflows/
    └── deploy.yml             # test-backend → test-frontend → build-and-deploy
```

**Structure Decision**: Web application (Option 2). Separate `backend/` and
`frontend/` trees at repository root. The backend enforces a strict 4-layer
architecture (constitution §I). Tests live adjacent to each layer they cover,
mirrored to `tests/unit/services/`, `tests/unit/repositories/`, and
`tests/integration/routers/` (constitution §V).

## Complexity Tracking

> No constitutional violations — this table intentionally left empty.
