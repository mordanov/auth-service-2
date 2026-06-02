from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models.user import UserAppAccess
from schemas.auth import VerifyTokenResponse
from services.token_service import TokenService

router = APIRouter(tags=["verify"])


@router.get("/api/verify-token", response_model=VerifyTokenResponse)
async def verify_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
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

    result = await db.execute(
        select(UserAppAccess)
        .where(UserAppAccess.user_id == user.id)
        .where(UserAppAccess.is_enabled.is_(True))
    )
    enabled_apps = [row.app_name for row in result.scalars().all()]

    return VerifyTokenResponse(
        user_id=user.id,
        username=user.username,
        role=user.role,
        apps=enabled_apps,
    )
