<!--
SYNC IMPACT REPORT
==================
Version change: [NEW] → 1.0.0 (initial ratification)
Modified principles: n/a — initial constitution, no prior version
Added sections:
  - Core Principles (I–VI: Separation of Concerns, Extensibility via Abstraction,
    DRY, KISS, Test-Driven Quality, Security by Default)
  - Technology Stack Constraints
  - Development Workflow & CI/CD
  - Governance
Removed sections: n/a (initial)
Templates requiring updates:
  - .specify/templates/plan-template.md  ✅ Constitution Check gate aligns (references constitution file)
  - .specify/templates/spec-template.md  ✅ No mandatory sections altered
  - .specify/templates/tasks-template.md ✅ Task categories align with principles
Deferred TODOs: none
-->

# auth-app Constitution

## Core Principles

### I. Separation of Concerns (SOLID — Single Responsibility)

Each module, class, and React component MUST have exactly one clearly defined
responsibility. The backend MUST enforce a strict four-layer architecture:
**Routers → Services → Repositories → Models**. No router may contain business
logic; no service may issue raw SQL; no model may depend on a router. React
components MUST be split into pages (routing/composition), components (UI),
hooks (state/behaviour), and api (network). Violations require explicit
justification in the Complexity Tracking table of the implementation plan.

**Rationale**: Mixed responsibilities in auth-critical code are the primary
source of security regressions and untestable code paths.

### II. Extensibility via Abstraction (SOLID — OCP / LSP / ISP / DIP)

- **OCP**: Adding a new OAuth provider MUST require only a new class in
  `oauth_service.py` implementing the shared provider interface — no
  modification of existing auth flow code is permitted.
- **LSP**: Repository implementations MUST be substitutable; all unit tests
  MUST run against in-memory or mock repositories without modifying service
  code.
- **ISP**: Pydantic schemas for requests, responses, and DB models MUST be
  separate types; no schema may carry fields its consumer does not use.
- **DIP**: FastAPI `Depends()` MUST be used for all cross-cutting concerns
  (`get_db`, `require_auth`, `require_admin`); services MUST receive
  dependencies injected, never self-construct them.

**Rationale**: The auth gateway is a shared dependency for all family
applications; its internal contract must be stable while its OAuth provider
set can evolve independently.

### III. DRY — Centralized Shared Logic

- Token generation, validation, expiry calculation, and cleanup MUST live
  exclusively in `TokenService`; no other module may replicate this logic.
- Auth verification MUST be implemented once as the `require_auth` FastAPI
  dependency, reused across all protected routes within `auth-app` and across
  all protected applications via the reference `auth_middleware.py`.
- All UI text MUST be sourced from `ru.json` / `en.json` translation files;
  no hardcoded string literals are permitted in React components.

**Rationale**: Duplicated token or auth logic creates divergent code paths
that introduce security vulnerabilities over time.

### IV. KISS — Simplicity First

- FastAPI built-in features (dependency injection, background tasks, OpenAPI
  docs) MUST be preferred over third-party libraries that duplicate them.
- Docker-compose structure MUST mirror `budget-site`; introducing additional
  services requires explicit written justification.
- The admin UI MUST use HeroUI default components; custom styling MUST NOT be
  introduced.
- No feature may be implemented speculatively; all code MUST serve a current,
  explicitly specified requirement.

**Rationale**: Complexity in security-critical code is a liability, not an
asset. Every additional dependency is an additional attack surface.

### V. Test-Driven Quality (NON-NEGOTIABLE)

- Backend coverage MUST reach ≥ 80%, enforced via
  `pytest-cov --fail-under=80`; CI MUST block the merge on failure.
- Frontend coverage MUST reach ≥ 80%, enforced via
  `vitest --coverage --coverage.thresholds.lines=80`; CI MUST block on failure.
- Unit tests MUST cover: `TokenService`, `AuthService`, `UserService`, all
  repositories, and all routers.
- Test structure MUST mirror source layout:
  `tests/unit/services/`, `tests/unit/repositories/`,
  `tests/integration/routers/`.
- New functionality MUST NOT be merged without tests that bring coverage to or
  above the threshold.

**Rationale**: Auth failures have direct user impact across all family
applications; coverage gates are the minimum safety net, not a ceiling.

### VI. Security by Default

- All secrets MUST reside in `.env` only; no secret may be hardcoded or
  committed to the repository under any circumstances.
- Passwords MUST be hashed with bcrypt; plaintext passwords MUST NEVER be
  logged, stored, or returned in any API response.
- All database queries MUST use SQLAlchemy ORM parameterized statements; raw
  SQL with string interpolation is prohibited.
- Auth tokens MUST be delivered exclusively as `httpOnly`, `Secure`,
  `SameSite=Lax` cookies scoped to `.mainpage.com`.
- CORS MUST be restricted to `*.mainpage.com` origins; no wildcard `*`
  configuration is permitted in production.
- Docker images MUST run as a non-root user.
- Blocking a user MUST atomically invalidate all their active tokens within
  the same database transaction; partial invalidation is a defect.

**Rationale**: `auth-app` is the single point of authentication for all
family applications; its security properties are non-negotiable and not
subject to trade-offs for developer convenience.

## Technology Stack Constraints

The following technology choices are mandated for `auth-app` and MUST NOT be
substituted without a formal constitution amendment:

| Layer | Mandated Technology |
|---|---|
| Frontend | React.js + HeroUI (default theme, no style overrides) |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL — shared instance from `web-folders` |
| ORM | SQLAlchemy 2.x + Alembic (migrations) |
| Web Server | Nginx — shared instance from `web-folders` |
| Containers | Docker + docker-compose (pattern mirrors `budget-site`) |
| Auth tokens | Opaque tokens (64 hex chars), stored in PostgreSQL |
| OAuth | Google OAuth2 + GitHub OAuth (authorization code flow) |
| Password hashing | bcrypt |
| HTTP client | httpx (async) |
| Background jobs | APScheduler or FastAPI background tasks |
| Backend testing | pytest + pytest-asyncio + pytest-cov |
| Frontend testing | Vitest + React Testing Library |
| i18n | react-i18next (Russian + English) |
| CI/CD | GitHub Actions |

**Shared infrastructure**: The `web-folders` Nginx and PostgreSQL instances
MUST be reused; `auth-app` MUST NOT provision its own database or web server
containers.

**Domain**: Cookie domain MUST be `.mainpage.com`; the canonical hostname for
this service is `auth.mainpage.com`.

**Databases**: Only the `users`, `user_app_access`, `auth_tokens`, and
`auth_logs` tables are owned by this service; no cross-service schema
mutations are permitted.

## Development Workflow & CI/CD

### Branch Strategy

All feature work MUST be developed on a feature branch following the naming
convention `###-feature-name`. Merges to `main` trigger the full CI/CD
pipeline automatically.

### CI Gate Requirements

The following jobs MUST all pass before any merge to `main` is accepted:

1. **`test-backend`** — Python 3.12, `pytest --cov=. --cov-fail-under=80`.
   Failure blocks deployment.
2. **`test-frontend`** — Node LTS, `npm run test:coverage` with ≥ 80% line
   threshold. Failure blocks deployment.
3. **`build-and-deploy`** — Docker Buildx build + registry push, SSH deploy,
   `alembic upgrade head`, health check `GET https://auth.mainpage.com/health`.
   Depends on both test jobs passing.

### Deployment Contract

- Database migrations MUST run via `alembic upgrade head` on every deployment,
  before traffic is served.
- `GET /health → 200 {"status": "ok"}` MUST succeed before the deployment is
  considered complete; CI MUST fail if this check does not pass.
- Required GitHub Secrets (MUST be documented and rotated per security policy):
  `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DOCKER_USERNAME`,
  `DOCKER_PASSWORD`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
  `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.

### Integration Contract for Protected Applications

Every application integrating with `auth-app` MUST follow this checklist:

1. Remove its own login pages, session middleware, and password checks.
2. Add `auth_middleware.py` (reference implementation provided) for backend
   route protection.
3. Add `checkAuth()` / `useAuth.js` (reference implementation provided) to the
   React entry point or router guard.
4. Use `credentials: 'include'` on all API fetch calls.
5. Configure Nginx `proxy_cookie_domain` to forward `auth_token` across the
   `.mainpage.com` domain.

## Governance

This constitution supersedes all other practices, conventions, and informal
agreements for the `auth-app` project.

**Amendment procedure**:
1. Propose the change as a pull request modifying this file with an updated
   `CONSTITUTION_VERSION` and `LAST_AMENDED_DATE`.
2. State the motivation, affected principles, and migration plan in the PR
   description.
3. Update all dependent templates (`plan-template.md`, `spec-template.md`,
   `tasks-template.md`) in the same PR.
4. Version bumps follow semantic versioning:
   - **MAJOR**: backward-incompatible principle removals or redefinitions.
   - **MINOR**: new principles added or material expansions of existing ones.
   - **PATCH**: clarifications, wording fixes, non-semantic refinements.

**Compliance**:
- All implementation plans MUST include a "Constitution Check" section
  confirming compliance with applicable principles before Phase 0 begins.
- Violations require an entry in the Complexity Tracking table with explicit
  justification approved by the project owner.
- CI gates are the automated enforcement layer; passing CI is necessary but
  not sufficient for full constitutional compliance.
- Any code review that identifies a constitutional violation MUST block merge
  until the violation is resolved or formally justified.

**Version**: 1.0.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-05-31