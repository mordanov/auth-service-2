# Feature Specification: Centralized Authentication Gateway

**Feature Branch**: `001-auth-middleware-app`
**Created**: 2026-05-31
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Authenticated User Accesses a Protected Application (Priority: P1)

A registered user navigates directly to a protected family application (e.g., budget tracker). The application has no login page of its own. If the user already holds a valid session token, they see the application immediately. If they do not, they are redirected to the central login page and returned to the original URL after successful sign-in.

**Why this priority**: This is the primary value proposition of the entire system. Every other story depends on the redirect-and-return flow working correctly.

**Independent Test**: Open a protected application URL in a fresh browser session with no cookies → verify redirect to login page → sign in → verify return to the original URL with the application fully loaded.

**Acceptance Scenarios**:

1. **Given** a user with a valid, non-expired token visits a protected application, **When** the application checks the token, **Then** the user sees the application content without any redirect.
2. **Given** a user with no token visits a protected application, **When** the application middleware checks authentication, **Then** the user is redirected to `https://auth.mainpage.com/login?redirect=<original-url>`.
3. **Given** a user with an expired token visits a protected application, **When** the middleware verifies the token, **Then** the user is redirected to the login page with the original URL preserved.
4. **Given** a blocked user whose token has not yet expired visits a protected application, **When** the middleware verifies the token, **Then** the user is refused access and redirected to the login page.

---

### User Story 2 — User Signs In with Username and Password (Priority: P1)

A user lands on the login page, enters their username and password, and gains access. On success they are redirected back to the application they were trying to reach (or to a default home if no redirect was specified). On failure they see a clear error message without any security-sensitive information disclosed.

**Why this priority**: Password login is the baseline authentication method; all user accounts support it regardless of OAuth provider status.

**Independent Test**: Navigate to `/login`, enter valid credentials → verify redirect to target application. Then enter invalid credentials → verify error message appears, no redirect.

**Acceptance Scenarios**:

1. **Given** valid credentials and a `redirect` query parameter, **When** the user submits the login form, **Then** a valid token cookie is set and the user is redirected to the `redirect` URL.
2. **Given** incorrect credentials, **When** the user submits the login form, **Then** an error message is displayed and no token is issued.
3. **Given** a blocked user's credentials, **When** the user attempts to log in, **Then** access is denied regardless of whether the password is correct.
4. **Given** a valid login, **When** the token is issued, **Then** the cookie is `httpOnly`, `Secure`, `SameSite=Lax`, scoped to `.mainpage.com`, and expires after the configured TTL.

---

### User Story 3 — User Signs In via Google or GitHub OAuth (Priority: P2)

A user clicks "Sign in with Google" or "Sign in with GitHub" on the login page. After completing the OAuth flow with the provider, the system looks up the user by their verified email address. If a matching active account exists, the user is granted access. If no account exists, access is denied without auto-registering a new account.

**Why this priority**: OAuth login is a convenience path for pre-registered users; the system remains secure because accounts must be pre-created by an admin.

**Independent Test**: Click "Sign in with Google" → complete Google OAuth → verify redirect to the target application for a known user. Attempt with an email not in the system → verify access is denied.

**Acceptance Scenarios**:

1. **Given** a Google/GitHub account whose email matches an active user record, **When** the OAuth callback is received, **Then** a token is issued and the user is redirected to the target application.
2. **Given** a Google/GitHub account whose email does not match any user record, **When** the OAuth callback is received, **Then** the user receives a 403 response and no account is created.
3. **Given** a Google/GitHub account matching a blocked user, **When** the OAuth callback is received, **Then** access is denied.
4. **Given** a completed OAuth flow, **When** the user's email is verified by the provider, **Then** only the primary verified email is used for account matching.

---

### User Story 4 — Admin Manages Users and Application Access (Priority: P2)

An admin logs in to the auth application and uses the admin panel to create new user accounts, block existing ones, and configure which of the 8 protected applications each user may access. The admin cannot delete users. Non-admin users cannot reach the admin panel.

**Why this priority**: Without admin tooling, user management requires direct database access, which is not acceptable for day-to-day operations.

**Independent Test**: Log in as admin → navigate to `/admin` → create a new user with access to two applications → log out → log in as the new user → verify access to those two applications → log in as admin → block the user → attempt to log in as the blocked user → verify denial.

**Acceptance Scenarios**:

1. **Given** an admin user, **When** they navigate to `/admin`, **Then** they see the full user list with name, email, role, and active/blocked status.
2. **Given** an admin creates a new user with a username, password, and selected app access, **When** the form is submitted, **Then** the user is persisted and can immediately log in.
3. **Given** an admin blocks a user, **When** the block action is confirmed, **Then** all active tokens for that user are immediately invalidated and the user cannot log in.
4. **Given** a `user`-role account, **When** they attempt to navigate to `/admin`, **Then** they are redirected to the login page or shown an access-denied response.
5. **Given** an admin updates a user's app access checkboxes, **When** the changes are saved, **Then** the token verification endpoint reflects the updated app list on the user's next request.

---

### User Story 5 — Token Verification by a Protected Application (Priority: P1)

A protected backend application calls the token verification endpoint to confirm whether an incoming request carries a valid token and to retrieve the user's identity and permitted applications.

**Why this priority**: This endpoint is the integration contract that all 8 protected applications depend on; it must be reliable and well-defined before any integration work can begin.

**Independent Test**: Issue a token via login → call `GET /api/verify-token` with the token in a cookie → verify `200` response with correct `user_id`, `username`, `role`, and `apps`. Repeat with an expired token → verify `401`. Repeat with a token belonging to a blocked user → verify `401`.

**Acceptance Scenarios**:

1. **Given** a valid, non-expired token sent as a cookie or `Authorization: Bearer` header, **When** `GET /api/verify-token` is called, **Then** the response is `200` with `user_id`, `username`, `role`, and `apps` fields.
2. **Given** an expired token, **When** the verification endpoint is called, **Then** the response is `401 {"error": "unauthorized"}`.
3. **Given** no token is present, **When** the endpoint is called, **Then** the response is `401 {"error": "unauthorized"}`.
4. **Given** a token belonging to a blocked user, **When** the endpoint is called, **Then** the response is `401 {"error": "unauthorized"}`.
5. **Given** a valid token for a user who lacks permission for a specific application, **When** the endpoint is called, **Then** the response is `200` but the `apps` array does not include that application.

---

### Edge Cases

- What happens when a Google/GitHub account email changes after account creation? The user loses OAuth login ability until an admin updates their email.
- What happens when the auth service is temporarily unavailable? Protected applications cannot verify tokens; they should return a service-unavailable error rather than silently allowing access.
- What happens when an admin attempts to create a duplicate username or email? The system returns a clear validation error; no partial record is persisted.
- What happens when `TOKEN_TTL_HOURS` is set to 0 or a very large value? Tokens still follow the configured value; documentation must warn that 0 creates immediately-expired tokens.
- What happens when two concurrent login requests arrive for the same user? Both succeed and issue independent tokens; users may hold multiple valid tokens simultaneously.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST issue an opaque token after any successful authentication (password, Google OAuth, or GitHub OAuth) and deliver it as an `httpOnly`, `Secure`, `SameSite=Lax` cookie named `auth_token` scoped to `.mainpage.com`.
- **FR-002**: The system MUST validate an incoming token (via cookie or `Authorization: Bearer` header) and return the user's identity and permitted applications when valid.
- **FR-003**: The system MUST redirect unauthenticated users to the login page, preserving the originally requested URL as a `redirect` query parameter.
- **FR-004**: The system MUST support login via username/password with passwords stored as bcrypt hashes; plaintext passwords MUST never be logged or stored.
- **FR-005**: The system MUST support login via Google OAuth2 authorization code flow, matching users by verified email address; unknown emails MUST be denied with no auto-registration.
- **FR-006**: The system MUST support login via GitHub OAuth, matching users by primary verified email address; unknown emails MUST be denied with no auto-registration.
- **FR-007**: The system MUST provide an admin panel accessible only to users with the `admin` role, where admins can create users, block/unblock users, and manage per-user access to the 8 protected applications.
- **FR-008**: The system MUST NOT support user deletion; only blocking is permitted.
- **FR-009**: Blocking a user MUST immediately invalidate all active tokens for that user.
- **FR-010**: The system MUST seed an initial admin user and two standard users from environment variables on first run.
- **FR-011**: Token TTL MUST be configurable via environment variable (`TOKEN_TTL_HOURS`, default 24 hours).
- **FR-012**: The system MUST run a background task to delete expired tokens on a regular schedule (at least once per hour).
- **FR-013**: The system MUST log all authentication attempts (successful and failed) including username, IP address, method, and reason for failure.
- **FR-014**: The system MUST provide a health check endpoint (`GET /health`) returning `200 {"status": "ok"}`.
- **FR-015**: The UI MUST support Russian and English languages with a visible language switcher; all user-facing strings MUST be sourced from translation files.

### Key Entities

- **User**: Represents a person who can authenticate. Has a username, optional email, optional bcrypt-hashed password, role (`admin` or `user`), active/blocked status, and optional OAuth provider IDs (Google, GitHub).
- **UserAppAccess**: A record linking a user to a specific protected application with an enabled/disabled flag. One record per user-application pair.
- **AuthToken**: An opaque token issued after successful authentication. Has a cryptographically random value, expiry timestamp, creation timestamp, last-used timestamp, and a reference to the owning user.
- **AuthLog**: An immutable audit record of each authentication attempt. Contains username, IP address, authentication method, success flag, failure reason, and timestamp.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a valid session reaches a protected application within 2 seconds of clicking a link (end-to-end including token verification round-trip).
- **SC-002**: All 8 protected applications successfully integrate with the token verification endpoint and have no remaining local login logic within one deployment cycle.
- **SC-003**: An admin can create a new user and grant application access in under 2 minutes using only the admin panel, with no direct database access required.
- **SC-004**: Blocking a user prevents all subsequent authentication attempts within 1 second of the block action completing.
- **SC-005**: The authentication service achieves 99.9% availability, measured over a 30-day rolling window.
- **SC-006**: Zero authentication bypass incidents: a blocked or token-less user cannot reach any protected application content under normal operating conditions.
- **SC-007**: All login attempts (success and failure) are captured in the audit log with no gaps; the log is queryable by admin.

---

## Assumptions

- All protected applications run on subdomains of `.mainpage.com`, enabling the shared cookie domain to work without cross-origin complications.
- The shared PostgreSQL and Nginx instances in `web-folders` are already running and accessible; `auth-app` does not provision its own database or web server.
- Each of the 8 protected applications is a FastAPI backend with a React frontend; the reference `auth_middleware.py` and `useAuth.js` patterns are directly applicable.
- Users for OAuth login are pre-created by an admin; the OAuth provider is used only as an identity verifier, not as a user source.
- The production environment enforces HTTPS for all services; `Secure` cookie flag is always valid in production.
- The language switcher defaults to the browser's preferred language; the chosen language is persisted in `localStorage`.
- Admins do not need access to protected applications; their role is limited to managing the auth service itself.
- No rate limiting or account lockout after failed login attempts is required for the initial version (this is a private family system with known users).
- Docker Compose structure and CI/CD pipeline conventions follow the existing `budget-site` application in the same repository.
