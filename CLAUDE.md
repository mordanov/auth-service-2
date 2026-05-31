<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan.

## Project: auth-app

**Business Source of Truth**: `prompt/auth-middleware-prompt.md`

This project builds **auth-app** — a centralized authentication gateway that acts as the single entry point for 8 existing family web applications. All feature specifications must preserve the product scope, technology stack, and domain model described in `prompt/auth-middleware-prompt.md` unless a formal change is approved.

### Technology Stack (non-negotiable constraints)

| Layer       | Technology                                                    |
|-------------|---------------------------------------------------------------|
| Frontend    | React.js + HeroUI (default style, no customization)          |
| Backend     | Python 3.12 + FastAPI                                         |
| Database    | PostgreSQL shared from `web-folders`                          |
| Web Server  | Nginx from `web-folders`                                      |
| Containers  | Docker + docker-compose                                       |
| i18n        | Russian and English (language switcher in UI)                 |

### Domain Model

- **users**: id, username, email, password_hash (bcrypt, nullable for OAuth-only), role (`admin`|`user`), is_active, google_id, github_id, created_at
- **user_app_access**: user_id FK, app_name, is_enabled — controls which of the 8 apps each user can access
- **auth_tokens**: token_value (64-char random opaque string), user_id FK, expires_at, created_at, last_used_at
- **auth_logs**: records every login attempt (success and failure) with actor and timestamp

### Authentication Methods

1. **Username/Password** — bcrypt hashed; seed creates 3 users from `.env` on first run
2. **Google OAuth2** — existing accounts only (match by email); unknown emails are denied; no auto-registration
3. **GitHub OAuth** — same policy as Google

### Core API Surface

- `GET /api/verify-token` → `{ user_id, username, role, apps }` (200) or `{ error: "unauthorized" }` (401) — called by all 8 protected apps
- `POST /login`, `POST /logout`, `GET /callback/google`, `GET /callback/github`
- `GET/POST /api/admin/users` — admin creates/blocks users (no deletion)
- `GET/POST /api/admin/apps` — admin toggles per-user app access checkboxes

### Protected Applications (fixed list)

`budget-site`, `family-admin-routine`, `family-archive`, `family-kitchen-recipes`, `new-site`, `portuguese-expenses`, `reminders-app`, `servinga-dashboard`

### Token Delivery

httpOnly cookie `auth_token`, `SameSite=Lax`, `Secure`, domain `.mainpage.com` (from `COOKIE_DOMAIN` env var), TTL from `TOKEN_TTL_HOURS` env var (default 24h).

### Roles

- **admin**: access to auth-app only; can create/block users; manages per-user app access checkboxes; views user list
- **user**: access to permitted applications only; no admin panel

### Speckit-Specify Instructions

When running `/speckit-specify` for this project:

1. Always treat `prompt/auth-middleware-prompt.md` as the source of truth for scope and constraints.
2. Do not introduce technologies outside the stack above (e.g., no JWT, no Redis, no TypeScript, no other CSS frameworks).
3. Functional requirements must reference the correct domain entities (`users`, `user_app_access`, `auth_tokens`, `auth_logs`) and API endpoints.
4. Success criteria must include: `docker compose up --build` starts successfully; all three auth methods work; admin panel allows user and access management; `GET /api/verify-token` returns correct data for valid tokens; expired/invalid tokens return 401; `auth_logs` records attempts; OpenAPI docs reachable at `/docs`.
5. Assumptions section must state: PostgreSQL is provided by the shared `web-folders` instance; Nginx is configured in `web-folders`; secrets come from `.env` only; no auto-registration for OAuth users.
<!-- SPECKIT END -->
