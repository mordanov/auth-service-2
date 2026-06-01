from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from models.log import AuthLog
from repositories.user_repository import UserRepository
from repositories.log_repository import LogRepository
from services.token_service import TokenService

_pwd_ctx = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# Pre-computed hash used for constant-time dummy verification when user not found.
# Prevents timing side-channels that enable username enumeration.
_DUMMY_HASH = _pwd_ctx.hash("__dummy__")


def _get_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")


class AuthService:
    @staticmethod
    async def login(
        username: str,
        password: str,
        db: AsyncSession,
        request: Request | None = None,
    ) -> tuple[str | None, str | None]:
        """Returns (token_value, failure_reason). failure_reason is None on success."""
        user_repo = UserRepository(db)
        log_repo = LogRepository(db)
        ip = _get_ip(request)

        user = await user_repo.get_by_username(username)

        if user is None or user.password_hash is None:
            # Always run bcrypt verify to normalise response time regardless of
            # whether the username exists, preventing timing-based enumeration.
            _pwd_ctx.verify(password, _DUMMY_HASH)
            await log_repo.create(
                AuthLog(
                    username=username,
                    ip_address=ip,
                    method="password",
                    success=False,
                    reason="invalid_credentials",
                )
            )
            await db.commit()
            return None, "invalid_credentials"

        if not _pwd_ctx.verify(password, user.password_hash):
            await log_repo.create(
                AuthLog(
                    username=username,
                    ip_address=ip,
                    method="password",
                    success=False,
                    reason="invalid_credentials",
                )
            )
            await db.commit()
            return None, "invalid_credentials"

        if not user.is_active:
            await log_repo.create(
                AuthLog(
                    username=username,
                    ip_address=ip,
                    method="password",
                    success=False,
                    reason="user_blocked",
                )
            )
            await db.commit()
            return None, "user_blocked"

        token_value = await TokenService.generate_token(user.id, db)
        await log_repo.create(
            AuthLog(
                username=username,
                ip_address=ip,
                method="password",
                success=True,
            )
        )
        await db.commit()
        return token_value, None

    @staticmethod
    async def oauth_login(
        provider: str,
        email: str,
        provider_user_id: str,
        db: AsyncSession,
        request: Request | None = None,
    ) -> str | None:
        user_repo = UserRepository(db)
        log_repo = LogRepository(db)
        ip = _get_ip(request)

        user = await user_repo.get_by_email(email)

        if user is None:
            await log_repo.create(
                AuthLog(
                    username=email,
                    ip_address=ip,
                    method=provider,
                    success=False,
                    reason="unknown_oauth_email",
                )
            )
            await db.commit()
            return None

        if not user.is_active:
            await log_repo.create(
                AuthLog(
                    username=user.username,
                    ip_address=ip,
                    method=provider,
                    success=False,
                    reason="user_blocked",
                )
            )
            await db.commit()
            return None

        if provider == "google" and not user.google_id:
            user.google_id = provider_user_id
        elif provider == "github" and not user.github_id:
            user.github_id = provider_user_id

        token_value = await TokenService.generate_token(user.id, db)
        await log_repo.create(
            AuthLog(
                username=user.username,
                ip_address=ip,
                method=provider,
                success=True,
            )
        )
        await db.commit()
        return token_value
