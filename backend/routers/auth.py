import secrets
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from schemas.auth import LoginRequest, LoginResponse
from services.auth_service import AuthService
from services.oauth_service import GoogleOAuthProvider, GitHubOAuthProvider
from repositories.token_repository import TokenRepository
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

_google = GoogleOAuthProvider()
_github = GitHubOAuthProvider()

ALLOWED_REDIRECT_SUFFIX = ".mainpage.com"

# Server-side OAuth state store: nonce → (redirect_url, expires_at)
# Short-lived (10 min TTL). The nonce is a cryptographically random string;
# the redirect URL is never embedded in the state parameter (prevents CSRF).
_oauth_state_store: dict[str, tuple[str, datetime]] = {}
_STATE_TTL_MINUTES = 10


def _create_oauth_state(redirect_url: str) -> str:
    nonce = secrets.token_urlsafe(32)
    _oauth_state_store[nonce] = (redirect_url, datetime.utcnow() + timedelta(minutes=_STATE_TTL_MINUTES))
    return nonce


def _consume_oauth_state(nonce: str) -> str | None:
    """Validate and consume a state nonce. Returns the stored redirect URL or None."""
    entry = _oauth_state_store.pop(nonce, None)
    if entry is None:
        return None
    redirect_url, expires_at = entry
    if datetime.utcnow() > expires_at:
        return None
    return redirect_url


def _is_safe_redirect(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in ("http", "https") and (
            parsed.netloc.endswith(ALLOWED_REDIRECT_SUFFIX)
            or parsed.netloc == "mainpage.com"
        )
    except Exception:
        return False


def _set_auth_cookie(response: Response, token_value: str) -> None:
    is_prod = settings.ENVIRONMENT == "production"
    kwargs = dict(
        key="auth_token",
        value=token_value,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.TOKEN_TTL_HOURS * 3600,
    )
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(**kwargs)


def _clear_auth_cookie(response: Response) -> None:
    is_prod = settings.ENVIRONMENT == "production"
    kwargs = dict(
        key="auth_token",
        httponly=True,
        secure=is_prod,
        samesite="lax",
    )
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(**kwargs)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    redirect: str = "",
    db: AsyncSession = Depends(get_db),
):
    token_value, failure_reason = await AuthService.login(body.username, body.password, db, request)

    if token_value is None:
        if failure_reason == "user_blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials"},
        )

    _set_auth_cookie(response, token_value)
    safe_redirect = redirect if redirect and _is_safe_redirect(redirect) else None
    return LoginResponse(message="ok", redirect=safe_redirect)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token_value = request.cookies.get("auth_token")
    if token_value:
        token_repo = TokenRepository(db)
        token = await token_repo.get_by_value(token_value)
        if token:
            await token_repo.delete(token)
            await db.commit()
    _clear_auth_cookie(response)
    return {"message": "ok"}


@router.get("/google")
async def google_auth(redirect: str = ""):
    safe_redirect = redirect if redirect and _is_safe_redirect(redirect) else ""
    state = _create_oauth_state(safe_redirect)
    url = _google.get_authorization_url(state)
    return RedirectResponse(url, status_code=302)


@router.get("/callback/google")
async def google_callback(
    code: str = "",
    state: str = "",
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    # Empty or unknown state means missing/forged CSRF nonce — reject.
    if not state:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )
    redirect_url = _consume_oauth_state(state)
    if redirect_url is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    try:
        token_data = await _google.exchange_code(code)
        access_token = token_data.get("access_token")
        result = await _google.get_verified_email(access_token)
    except Exception:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    if result is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    email, provider_id = result
    token_value = await AuthService.oauth_login("google", email, provider_id, db, request)

    if token_value is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    destination = redirect_url if redirect_url else settings.AUTH_APP_URL
    response = RedirectResponse(destination, status_code=302)
    _set_auth_cookie(response, token_value)
    return response


@router.get("/github")
async def github_auth(redirect: str = ""):
    safe_redirect = redirect if redirect and _is_safe_redirect(redirect) else ""
    state = _create_oauth_state(safe_redirect)
    url = _github.get_authorization_url(state)
    return RedirectResponse(url, status_code=302)


@router.get("/callback/github")
async def github_callback(
    code: str = "",
    state: str = "",
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    # Empty or unknown state means missing/forged CSRF nonce — reject.
    if not state:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )
    redirect_url = _consume_oauth_state(state)
    if redirect_url is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    try:
        token_data = await _github.exchange_code(code)
        access_token = token_data.get("access_token")
        result = await _github.get_verified_email(access_token)
    except Exception:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    if result is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    email, provider_id = result
    token_value = await AuthService.oauth_login("github", email, provider_id, db, request)

    if token_value is None:
        return RedirectResponse(
            f"{settings.AUTH_APP_URL}/login?error=forbidden", status_code=302
        )

    destination = redirect_url if redirect_url else settings.AUTH_APP_URL
    response = RedirectResponse(destination, status_code=302)
    _set_auth_cookie(response, token_value)
    return response
