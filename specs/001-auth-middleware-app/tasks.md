---
description: "Task list for auth-app — Centralized Authentication Gateway"
---

# Tasks: Centralized Authentication Gateway

**Input**: Design documents from `specs/001-auth-middleware-app/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, quickstart.md ✅

**Multi-agent execution**: Tasks are tagged with agent roles for `run-agents.sh` / brainstorm MCP
coordination. Role tags: `[BACKEND]` `[FRONTEND]` `[PLATFORM]` `[ARCH]` `[SECURITY-CRITICAL]`
`[OPS]` — these indicate the owning agent and any required review gates.

**Tests**: Test tasks are included because the constitution mandates ≥ 80% coverage enforced in CI.

## Format: `[ID] [P?] [Story?] [RoleTag] Description — file path`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1–US5)
- **[RoleTag]**: Primary agent owner for brainstorm MCP coordination
- Include exact file paths in all task descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create the repository structure and initialize both backend and frontend projects.
All setup tasks can run in parallel after T001.

- [ ] T001 Create repository directory structure as defined in plan.md: `backend/`, `frontend/`, `backend/routers/`, `backend/services/`, `backend/repositories/`, `backend/models/`, `backend/schemas/`, `backend/db/`, `backend/tasks/`, `backend/alembic/`, `frontend/src/`, `frontend/src/api/`, `frontend/src/hooks/`, `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/i18n/`, `frontend/tests/`, `tests/unit/services/`, `tests/unit/repositories/`, `tests/integration/routers/`, `.github/workflows/`
- [ ] T002 [P] [BACKEND] Initialize Python 3.12 backend project: create `backend/requirements.txt` with fastapi, sqlalchemy[asyncio], asyncpg, alembic, passlib[bcrypt], httpx, pydantic-settings, pytest, pytest-asyncio, pytest-cov, python-multipart, APScheduler
- [ ] T003 [P] [FRONTEND] Initialize React+Vite frontend project: create `frontend/package.json` with react, react-dom, react-router-dom, @heroui/react, react-i18next, i18next, vitest, @testing-library/react, @vitest/coverage-v8
- [ ] T004 [P] [BACKEND] Initialize Alembic in `backend/alembic/` with async SQLAlchemy target metadata pointing to `backend/models/`
- [ ] T005 [P] [PLATFORM] Create `.env.example` at repository root with all variables from spec section 15: DATABASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD, USER1_USERNAME, USER1_PASSWORD, USER2_USERNAME, USER2_PASSWORD, TOKEN_TTL_HOURS, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI, AUTH_APP_URL, COOKIE_DOMAIN, ENVIRONMENT, ALLOWED_ORIGINS
- [ ] T006 [P] [PLATFORM] Create root `.gitignore` covering `.env`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `dist/`, `htmlcov/`, `coverage/`, `.coverage`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be implemented.

⚠️ **CRITICAL**: No user story work begins until this phase is complete.

- [ ] T007 [P] [BACKEND] Implement pydantic-settings `Settings` class in `backend/config.py` exposing all env vars: DATABASE_URL, TOKEN_TTL_HOURS, SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI, AUTH_APP_URL, COOKIE_DOMAIN, ENVIRONMENT, ALLOWED_ORIGINS
- [ ] T008 [P] [BACKEND] Implement async SQLAlchemy engine + `AsyncSession` factory + `get_db` generator in `backend/db/database.py` using `asyncpg` driver and `DATABASE_URL` from config
- [ ] T009 [P] [BACKEND] [DATA] Create SQLAlchemy ORM models `User` and `UserAppAccess` in `backend/models/user.py` — columns and constraints exactly matching `data-model.md`
- [ ] T010 [P] [BACKEND] [DATA] Create SQLAlchemy ORM model `AuthToken` in `backend/models/token.py` — columns and constraints exactly matching `data-model.md`
- [ ] T011 [P] [BACKEND] [DATA] Create SQLAlchemy ORM model `AuthLog` in `backend/models/log.py` — INSERT-only, columns exactly matching `data-model.md`
- [ ] T012 [BACKEND] [DATA] Generate Alembic initial migration in `backend/alembic/versions/` creating tables: `users`, `user_app_access`, `auth_tokens`, `auth_logs` with all constraints, FKs, and UUID defaults
- [ ] T013 [BACKEND] Implement idempotent seed script in `backend/db/seed.py`: check if `users` table is empty; if so, bcrypt-hash passwords and INSERT 1 admin + 2 users from env vars ADMIN_USERNAME/ADMIN_PASSWORD, USER1_USERNAME/USER1_PASSWORD, USER2_USERNAME/USER2_PASSWORD; also INSERT `user_app_access` rows for all 8 apps with `is_enabled=FALSE` for each seeded user
- [ ] T014 [BACKEND] Create Pydantic request/response schemas in `backend/schemas/auth.py` (LoginRequest, LoginResponse, VerifyTokenResponse), `backend/schemas/user.py` (UserCreate, UserResponse, AppAccessItem, AppAccessListRequest), `backend/schemas/token.py` (TokenCreate — internal)
- [ ] T015 [BACKEND] Create FastAPI app factory in `backend/main.py`: app init, lifespan (start APScheduler), CORSMiddleware for `ALLOWED_ORIGINS`, mount routers (auth, verify, admin), `GET /health → {"status": "ok"}`, OpenAPI at `/docs`
- [ ] T016 [BACKEND] Implement shared FastAPI dependencies in `backend/dependencies.py`: `get_db` (from db/database.py), `require_auth` (token → 401 if missing/expired/blocked), `require_admin` (role check → 403 if not admin)
- [ ] T017 [P] [FRONTEND] Set up react-i18next in `frontend/src/i18n/index.js` with language detection from localStorage; create `frontend/src/i18n/ru.json` and `frontend/src/i18n/en.json` with keys for all UI strings (login form, errors, admin panel labels, language switcher)
- [ ] T018 [P] [FRONTEND] Create `frontend/src/App.jsx` with React Router v6: route `/login` → LoginPage, route `/admin` → AdminPage (guarded by useAuth check); wrap with `HeroUIProvider` and `I18nextProvider`; create `frontend/src/main.jsx` entry point

**Checkpoint**: Foundation ready — all user story phases can begin after T016 and T018 complete.

---

## Phase 3: User Story 2 — Password Login + Token Issuance (Priority: P1) 🎯 MVP

**Goal**: A user can sign in with username/password and receive a valid `auth_token` cookie.
Logout invalidates the token.

**Independent Test**: `POST /api/auth/login` with valid credentials → `200` + `Set-Cookie: auth_token`; with wrong credentials → `401`; `POST /api/auth/logout` → cookie cleared.

### Implementation for User Story 2

- [ ] T019 [P] [US2] [BACKEND] Implement `UserRepository` in `backend/repositories/user_repository.py`: `get_by_id()`, `get_by_username()`, `get_by_email()`, `create()`, `update_active_status()`, `list_all()`
- [ ] T020 [P] [US2] [BACKEND] Implement `TokenRepository` in `backend/repositories/token_repository.py`: `create()`, `get_by_value()`, `delete()`, `delete_by_user_id()`, `delete_expired()`
- [ ] T021 [P] [US2] [BACKEND] Implement `LogRepository` in `backend/repositories/log_repository.py`: `create()` (INSERT-only); never UPDATE or DELETE
- [ ] T022 [US2] [BACKEND] [SECURITY-CRITICAL] Implement `TokenService` in `backend/services/token_service.py`: `generate_token(user_id, db)` using `secrets.token_hex(32)`, `validate_token(token_value, db)` → UserResponse or None, `cleanup_expired(db)` — all token logic lives ONLY here
- [ ] T023 [US2] [BACKEND] [SECURITY-CRITICAL] Implement `AuthService.login(username, password, db)` in `backend/services/auth_service.py`: look up user by username, bcrypt verify password, check `is_active`, call `TokenService.generate_token()`, call `LogRepository.create()` for both success and failure; NEVER log plaintext password
- [ ] T024 [US2] [BACKEND] Implement hourly background token cleanup task in `backend/tasks/cleanup.py` using APScheduler `AsyncIOScheduler` with 1-hour `IntervalTrigger`; started in `main.py` lifespan; calls `TokenService.cleanup_expired()`
- [ ] T025 [US2] [BACKEND] Implement auth router in `backend/routers/auth.py`: `POST /api/auth/login` (call AuthService.login, set cookie with COOKIE_DOMAIN/httpOnly/Secure/SameSite=lax/max_age), `POST /api/auth/logout` (delete token via TokenRepository, clear cookie); register router in `main.py`
- [ ] T026 [P] [US2] [FRONTEND] Implement `LoginForm` component in `frontend/src/components/LoginForm.jsx`: username + password fields using HeroUI Input, submit button, error display — all strings via i18n keys
- [ ] T027 [P] [US2] [FRONTEND] Implement `LanguageSwitcher` component in `frontend/src/components/LanguageSwitcher.jsx`: RU/EN toggle using HeroUI Button, persists selection to localStorage, calls i18next.changeLanguage()
- [ ] T028 [US2] [FRONTEND] Add `login(username, password)` and `logout()` functions to `frontend/src/api/authApi.js` — both use `credentials: 'include'`; login POSTs to `/api/auth/login`; logout POSTs to `/api/auth/logout`
- [ ] T029 [US2] [FRONTEND] Implement `frontend/src/pages/LoginPage.jsx`: HeroUI Tabs (password tab + placeholder OAuth tab), render LoginForm + LanguageSwitcher in top-right corner; on login success, redirect to `?redirect` query param or default `/`

**Checkpoint**: Password login and logout fully functional and independently testable.

---

## Phase 4: User Story 5 — Token Verification Endpoint (Priority: P1)

**Goal**: Protected applications can verify a token and receive the user's identity + permitted apps.

**Independent Test**: Issue token via login → `GET /api/verify-token` with cookie → `200 {user_id, username, role, apps}`; expired token → `401`; no token → `401`; blocked user's token → `401`.

### Implementation for User Story 5

- [ ] T030 [US5] [BACKEND] [SECURITY-CRITICAL] Implement verify router in `backend/routers/verify.py`: `GET /api/verify-token` — read token from `Cookie: auth_token` first, then `Authorization: Bearer`; call `TokenService.validate_token()`; query `user_app_access` for enabled apps; update `last_used_at`; return `VerifyTokenResponse(user_id, username, role, apps)` on 200, `{"error": "unauthorized"}` on 401; register router in `main.py`
- [ ] T031 [US5] [BACKEND] Update `require_auth` dependency in `backend/dependencies.py` to call `TokenService.validate_token()` via injected `TokenRepository`; ensure blocked-user tokens return 401 not 403 (constitution §VI: token invalidated on block)
- [ ] T032 [US5] [FRONTEND] Implement `useAuth` hook in `frontend/src/hooks/useAuth.js`: calls `GET /api/verify-token` with `credentials: 'include'`; on 401 redirects to `https://auth.mainpage.com/login?redirect=<current href>`; on 200 returns user object; export `checkAuth()` for use in App.jsx router guard

**Checkpoint**: `/api/verify-token` returns correct data; protected applications can integrate.

---

## Phase 5: User Story 1 — Redirect-and-Return Flow (Priority: P1)

**Goal**: An unauthenticated user visiting a protected application is redirected to login and returned to the original URL after sign-in.

**Independent Test**: Browser with no cookie → navigate to protected app URL → verify redirect to `/login?redirect=<original-url>` → sign in → verify redirect back to original URL.

### Implementation for User Story 1

- [ ] T033 [US1] [BACKEND] Verify `POST /api/auth/login` in `backend/routers/auth.py` accepts `redirect` query parameter and returns it in the response body or as a redirect Location header after setting the cookie; ensure `redirect` URL is validated to prevent open redirect (must be under `.mainpage.com`)
- [ ] T034 [US1] [FRONTEND] Wire `checkAuth()` call in `frontend/src/App.jsx` router guard: on every page load that is not `/login`, call `checkAuth()`; on 401, redirect to `/login?redirect=<current href>`; on success, store user in React state
- [ ] T035 [US1] [ARCH] Add `docs/integration-guide.md` at repository root with the reference `auth_middleware.py` (Python FastAPI) and `useAuth.js` (React) integration snippets, Nginx `proxy_cookie_domain` example config, and the step-by-step checklist for protected app developers

**Checkpoint**: Full redirect-and-return flow works end-to-end in a browser.

---

## Phase 6: User Story 3 — OAuth Login: Google + GitHub (Priority: P2)

**Goal**: A user with a pre-existing account can sign in via Google or GitHub OAuth2. Unknown email addresses are denied with no auto-registration.

**Independent Test**: Browser → click "Sign in with Google" → complete OAuth → verify redirect + cookie set for known user; verify 403 redirect to `/login?error=forbidden` for unknown email.

### Implementation for User Story 3

- [ ] T036 [P] [US3] [BACKEND] [SECURITY-CRITICAL] Implement `GoogleOAuthProvider` in `backend/services/oauth_service.py`: `get_authorization_url(state)` builds Google OAuth2 URL with `client_id`, `scope=openid email`, `redirect_uri`; `exchange_code(code)` calls Google token endpoint; `get_verified_email(access_token)` returns the primary verified email only
- [ ] T037 [P] [US3] [BACKEND] [SECURITY-CRITICAL] Implement `GitHubOAuthProvider` in `backend/services/oauth_service.py` alongside Google provider: same interface — `get_authorization_url(state)`, `exchange_code(code)`, `get_verified_email(access_token)` (must call `/user/emails` and return primary verified email only, NOT `/user` profile email which may be unverified)
- [ ] T038 [US3] [BACKEND] [SECURITY-CRITICAL] Implement `AuthService.oauth_login(provider, code, db)` in `backend/services/auth_service.py`: call provider's `exchange_code()` + `get_verified_email()`; look up user by email via `UserRepository.get_by_email()`; if not found → log failure + return 403; if found but `is_active=False` → return 403; if found + active → store/update `google_id`/`github_id` on user row, call `TokenService.generate_token()`, log success; extend auth router with `GET /api/auth/google`, `GET /api/auth/callback/google`, `GET /api/auth/github`, `GET /api/auth/callback/github` endpoints; use `state` parameter to carry the `redirect` URL through the OAuth round-trip; validate `state` is a URL under `.mainpage.com`
- [ ] T039 [P] [US3] [FRONTEND] Implement `OAuthButtons` component in `frontend/src/components/OAuthButtons.jsx`: HeroUI Button for Google + Button for GitHub; each links to the respective `GET /api/auth/google` or `/api/auth/github` endpoint; show provider icons; all labels via i18n keys
- [ ] T040 [US3] [FRONTEND] Update `frontend/src/pages/LoginPage.jsx` tabs: add fully functional "Google" and "GitHub" tabs rendering `OAuthButtons` component; display error message from `?error=forbidden` query param if present

**Checkpoint**: OAuth login works for known users; unknown emails receive 403.

---

## Phase 7: User Story 4 — Admin Panel: User and Access Management (Priority: P2)

**Goal**: An admin can create users, block/unblock them, and manage per-user application access via a UI panel. Non-admin users cannot reach the panel.

**Independent Test**: Log in as admin → navigate to `/admin` → create user → enable 2 apps → log out → log in as new user → verify access to those 2 apps; block new user → verify login denied.

### Implementation for User Story 4

- [ ] T041 [P] [US4] [BACKEND] Implement `UserService` in `backend/services/user_service.py`: `create_user(data, db)` — bcrypt-hash password, INSERT user, INSERT `user_app_access` rows for all 8 apps with `is_enabled=FALSE`; `block_user(user_id, db)` — set `is_active=FALSE` AND DELETE all `auth_tokens` for that user in a single transaction; `update_app_access(user_id, app_list, db)` — upsert all 8 app access rows
- [ ] T042 [US4] [BACKEND] Implement admin router in `backend/routers/admin.py` behind `require_admin` dependency: `GET /api/admin/users` → list all users; `POST /api/admin/users` → call UserService.create_user(); `PATCH /api/admin/users/{user_id}` → call UserService.block_user() or unblock; `GET /api/admin/users/{user_id}/apps` → return all 8 app access rows; `PUT /api/admin/users/{user_id}/apps` → call UserService.update_app_access(); register router in `main.py`
- [ ] T043 [P] [US4] [FRONTEND] Implement `UserTable` component in `frontend/src/components/UserTable.jsx`: HeroUI Table showing username, email, role, active/blocked status; expandable row reveals `AppAccessCheckboxes`; "Block" button calls `patchUser()`; all labels via i18n keys
- [ ] T044 [P] [US4] [FRONTEND] Implement `UserCreateModal` component in `frontend/src/components/UserCreateModal.jsx`: HeroUI Modal with username + email (optional) + password fields; submits via `createUser()` API call; shows validation errors; all strings via i18n keys
- [ ] T045 [P] [US4] [FRONTEND] Implement `AppAccessCheckboxes` component in `frontend/src/components/AppAccessCheckboxes.jsx`: 8 HeroUI Checkboxes (one per protected app); renders current `is_enabled` state; calls `putApps()` on change; all app names and labels via i18n keys
- [ ] T046 [US4] [FRONTEND] Implement `frontend/src/pages/AdminPage.jsx`: render `UserTable`; include "Create user" HeroUI Button that opens `UserCreateModal`; fetch user list on mount via `getUsers()`; all labels via i18n
- [ ] T047 [US4] [FRONTEND] Extend `frontend/src/api/authApi.js` with admin calls: `getUsers()`, `createUser(data)`, `patchUser(id, data)`, `getApps(userId)`, `putApps(userId, apps)` — all use `credentials: 'include'`

**Checkpoint**: Admin panel fully functional; user management and access control work end-to-end.

---

## Phase 8: Platform — Docker, CI/CD, Nginx

**Purpose**: Containerization and deployment pipeline. Can begin in parallel with Phase 3 after Phase 2 completes.

- [ ] T048 [P] [PLATFORM] Write `backend/Dockerfile`: base `python:3.12-slim`, create non-root user `appuser`, copy `requirements.txt`, `pip install`, copy backend source, `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`
- [ ] T049 [P] [PLATFORM] Write `frontend/Dockerfile`: multi-stage — stage 1 `node:lts-alpine` runs `npm ci && npm run build`; stage 2 `nginx:alpine` copies `dist/` to nginx html root; non-root user
- [ ] T050 [PLATFORM] Write root `docker-compose.yml`: services `auth-app-backend` (build: backend/, port 8000, env_file .env, depends_on postgres via external network) and `auth-app-frontend` (build: frontend/); declare external network `web-folders_default` to connect to shared postgres + nginx
- [ ] T051 [PLATFORM] Write `.github/workflows/deploy.yml`: job `test-backend` (Python 3.12, `pip install -r backend/requirements.txt`, `pytest --cov=backend --cov-fail-under=80`, upload coverage artifact); job `test-frontend` (Node LTS, `npm ci` in frontend/, `npm run test:coverage`, upload artifact); job `build-and-deploy` (needs both test jobs, Docker Buildx, registry push, SSH deploy, `docker-compose up -d --build`, `alembic upgrade head`, `curl -f https://auth.mainpage.com/health`); document required GitHub Secrets: DEPLOY_SSH_KEY, DEPLOY_HOST, DEPLOY_USER, DOCKER_USERNAME, DOCKER_PASSWORD, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
- [ ] T052 [PLATFORM] [ARCH] Create `docs/nginx/auth.mainpage.com.conf`: nginx `server` block for `auth.mainpage.com` proxying to `auth-app-backend:8000` with `proxy_set_header` Host, X-Real-IP, X-Forwarded-For; create `docs/nginx/protected-app-example.conf`: example config showing `proxy_cookie_domain auth.mainpage.com .mainpage.com`

---

## Phase 9: Tests — Coverage Gates (≥ 80%)

**Purpose**: Test suite covering all services, repositories, and routers. Must run in CI. All test tasks are parallel within this phase.

### Backend Unit Tests

- [ ] T053 [P] [BACKEND] Write unit tests for `TokenService` in `tests/unit/services/test_token_service.py`: token generation produces 64 hex chars, validation returns correct user, expiry rejection, cleanup deletes correct rows, blocked user's token rejected; use mock `TokenRepository`
- [ ] T054 [P] [BACKEND] Write unit tests for `AuthService` (password branch) in `tests/unit/services/test_auth_service.py`: valid login issues token and logs success, wrong password logs failure returns None, blocked user rejected, correct bcrypt comparison; use mock repositories
- [ ] T055 [P] [BACKEND] Write unit tests for `AuthService` (OAuth branch) in `tests/unit/services/test_auth_service.py`: known email issues token, unknown email returns 403 and logs failure, blocked user returns 403, `google_id`/`github_id` stored on user row after first login; use mock repositories + mock OAuth providers
- [ ] T056 [P] [BACKEND] Write unit tests for `UserService` in `tests/unit/services/test_user_service.py`: create_user inserts user + 8 app access rows with is_enabled=FALSE, block_user sets is_active=FALSE + deletes all tokens atomically, update_app_access upserts all 8 rows correctly
- [ ] T057 [P] [BACKEND] Write unit tests for `UserRepository` in `tests/unit/repositories/test_user_repository.py`: get_by_username hit + miss, get_by_email hit + miss, create persists correctly, update_active_status; use async test DB or in-memory mock
- [ ] T058 [P] [BACKEND] Write unit tests for `TokenRepository` in `tests/unit/repositories/test_token_repository.py`: create, get_by_value hit + miss, delete, delete_by_user_id deletes all user tokens, delete_expired leaves valid tokens intact
- [ ] T059 [P] [BACKEND] Write unit tests for `LogRepository` in `tests/unit/repositories/test_log_repository.py`: create inserts all fields; verify no UPDATE or DELETE methods exist on the class
- [ ] T060 [P] [BACKEND] Write integration tests for auth router in `tests/integration/routers/test_auth_router.py`: successful login sets cookie, wrong password returns 401, blocked user returns 403, logout clears cookie; use `httpx.AsyncClient` with `ASGITransport`
- [ ] T061 [P] [BACKEND] Write integration tests for verify router in `tests/integration/routers/test_verify_router.py`: valid cookie returns 200 with correct fields, expired token returns 401, no token returns 401, blocked user's token returns 401, apps array matches enabled access rows
- [ ] T062 [P] [BACKEND] Write integration tests for admin router in `tests/integration/routers/test_admin_router.py`: non-admin request returns 403, list users, create user, block user invalidates tokens, get + put app access; use `httpx.AsyncClient`

### Frontend Unit Tests

- [ ] T063 [P] [FRONTEND] Write Vitest tests for `LoginForm` in `frontend/tests/LoginForm.test.jsx`: renders username + password fields, submit button disabled when empty, calls `authApi.login()` with correct args on submit, shows error message on API failure
- [ ] T064 [P] [FRONTEND] Write Vitest tests for `UserTable` in `frontend/tests/UserTable.test.jsx`: renders user rows with name/email/role/status, "Block" button triggers callback with user id, expandable row renders `AppAccessCheckboxes`
- [ ] T065 [P] [FRONTEND] Write Vitest tests for `AppAccessCheckboxes` in `frontend/tests/AppAccessCheckboxes.test.jsx`: renders 8 checkboxes, checked state reflects `is_enabled` prop, onChange propagates `putApps()` call with updated app list
- [ ] T066 [P] [FRONTEND] Write Vitest tests for `useAuth` hook in `frontend/tests/useAuth.test.js`: redirects to `/login?redirect=...` on 401 response, returns user object on 200 response; mock `fetch`
- [ ] T067 [P] [FRONTEND] Write Vitest tests for `LanguageSwitcher` in `frontend/tests/LanguageSwitcher.test.jsx`: renders RU and EN buttons, clicking EN calls `i18next.changeLanguage('en')`, selected language persists to localStorage

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Verify coverage gates, validate end-to-end, and confirm operational readiness.

- [ ] T068 [BACKEND] Run `pytest --cov=backend --cov-fail-under=80` from repository root and confirm exit code 0; if coverage below 80%, add missing tests until threshold is met
- [ ] T069 [FRONTEND] Run `npm run test:coverage` in `frontend/` and confirm all line-coverage thresholds ≥ 80% pass; if below threshold, add missing tests
- [ ] T070 [OPS] Verify `GET /health` returns `200 {"status": "ok"}` after `docker-compose up --build`; verify `GET /docs` returns FastAPI OpenAPI UI; verify `alembic upgrade head` runs without errors against the real DB from `web-folders`
- [ ] T071 [ARCH] Run through `specs/001-auth-middleware-app/quickstart.md` end-to-end validation: health check, password login, token verify, admin CRUD, block + token invalidation, logout, OAuth browser test, language switcher; record results and confirm all 10 sections pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; all tasks [P]
- **Foundational (Phase 2)**: Depends on T001–T006; BLOCKS all user story phases
- **US2 (Phase 3)**: Depends on Phase 2 completion; unblocked by T016 + T018
- **US5 (Phase 4)**: Depends on Phase 3 completion (needs TokenService + token issuance)
- **US1 (Phase 5)**: Depends on Phase 4 completion (needs `/api/verify-token` endpoint)
- **US3 (Phase 6)**: Depends on Phase 3 completion (needs AuthService + token issuance path)
- **US4 (Phase 7)**: Depends on Phase 2 completion; can proceed in parallel with Phase 3 after T016
- **Platform (Phase 8)**: Depends on Phase 2 completion; can run in parallel with Phase 3+
- **Tests (Phase 9)**: Depends on implementation phases (3–7); each test file is [P] once its target exists
- **Polish (Phase 10)**: Depends on all phases 3–9 completing

### User Story Dependencies

- **US2 (P1)**: Can start after Foundational — no inter-story dependencies
- **US5 (P1)**: Depends on US2 (needs token issuance to exist)
- **US1 (P1)**: Depends on US5 (needs `/api/verify-token` endpoint)
- **US3 (P2)**: Depends on US2 (reuses AuthService + TokenService)
- **US4 (P2)**: Depends on Foundational only — no dependency on US2/US3

### Agent Assignment Summary (brainstorm MCP)

| Agent | Phase Ownership |
|---|---|
| `backend` | T002, T004, T007–T025, T028, T030–T032, T033, T036–T038, T041–T042, T048, T053–T062, T068 |
| `frontend` | T003, T017–T018, T026–T027, T029, T032, T034, T039–T040, T043–T047, T049, T063–T067, T069 |
| `devops` | T005–T006, T050–T052, T070 |
| `software-architect` | T001, T035, T052 (nginx docs), T071 |
| `security-architect` | Review T022, T023, T030, T031, T036, T037, T038 before merge |
| `autotester` | T053–T067, T068, T069, T071 |
| `code-reviewer` | Review all phases after completion |
| `product-manager` | Coordinate handoffs; validate checkpoints |
| `project-administrator` | Metrics collection; HTML report after T071 |

---

## Parallel Opportunities

### Phase 2: Run all in parallel once T001 completes

```
T007 (config.py) ──┐
T008 (database.py)─┤
T009 (models/user)─┤──→ T012 (migration, needs T009-T011)
T010 (models/token)┤
T011 (models/log)──┘
T014 (main.py) ────→ T015 (dependencies.py)
T016 (schemas)
T017 (i18n)
T018 (App.jsx)
```

### Phase 3: Parallel backend repos + frontend components

```
T019 (UserRepo) ──┐
T020 (TokenRepo)──┼──→ T022 (TokenService) → T023 (AuthService) → T025 (router)
T021 (LogRepo) ───┘
T026 (LoginForm) ──┐
T027 (LangSwitch)──┼──→ T029 (LoginPage)
T028 (authApi) ────┘
```

### Phase 9: All test files run in parallel

All T053–T067 can run concurrently once their target implementations exist.

---

## Implementation Strategy

### MVP (User Stories 2 + 5 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US2 (password login + logout + tokens)
4. Complete Phase 4: US5 (verify-token endpoint)
5. **STOP and VALIDATE**: `curl -X POST /api/auth/login` → token → `curl /api/verify-token` → 200
6. Protected applications can already integrate at this point

### Incremental Delivery

1. **MVP** (Phase 1–4): Login + token verification → protected apps can integrate
2. **+ Redirect flow** (Phase 5): Full browser redirect-and-return experience
3. **+ OAuth** (Phase 6): Google + GitHub login for convenience
4. **+ Admin panel** (Phase 7): User management without DB access
5. **+ Tests + CI** (Phases 8–9): Production-ready pipeline
6. **+ Validation** (Phase 10): End-to-end sign-off per quickstart.md

### Parallel Agent Strategy (brainstorm MCP)

With the full 9-agent team:

- **Phase 2**: `backend` agent owns T007–T016; `frontend` agent owns T017–T018
- **Phase 3–7**: `backend` and `frontend` agents work in parallel (different files)
- **Phase 8**: `devops` agent works in parallel with Phase 3+ (Docker/CI files have no source code deps)
- **Phase 9**: `autotester` agent claims all test tasks in parallel once implementations are stable
- **security-architect** reviews [SECURITY-CRITICAL] tasks as they land (T022, T023, T030, T031, T036–T038)
- **code-reviewer** reviews completed phases before handoff to next phase
- **project-administrator** collects metrics after every completed task via `../scripts/report-task-metrics.sh`

---

## Notes

- `[P]` = different files, no incomplete-task dependencies — safe to run in parallel
- `[US?]` maps to user story in spec.md for traceability
- `[SECURITY-CRITICAL]` tasks require `security-architect` review before merge
- Each user story phase is independently completable and testable
- Verify test failure before implementing (for TDD discipline)
- Commit after each task or logical group
- Stop at each checkpoint to validate the story independently
- `run-agents.sh --project auth-app` launches the full 9-agent team; agents read `specs/001-auth-middleware-app/` for context
