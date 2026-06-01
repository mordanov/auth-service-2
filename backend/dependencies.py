from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.user import User
from services.token_service import TokenService


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token_value = request.cookies.get("auth_token")
    if not token_value:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_value = auth_header[7:]

    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    user = await TokenService.validate_token(token_value, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    return user


async def require_admin(
    current_user: User = Depends(require_auth),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden"},
        )
    return current_user
