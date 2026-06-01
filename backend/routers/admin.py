from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from db.database import get_db
from dependencies import require_admin
from models.user import User, PROTECTED_APPS
from schemas.user import (
    UserCreate,
    UserResponse,
    UserPatch,
    UserPatchResponse,
    AppAccessItem,
)
from services.user_service import UserService
from repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    repo = UserRepository(db)
    users = await repo.list_all()
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if body.role not in ("user",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_role", "detail": "role must be 'user'"},
        )

    try:
        user = await UserService.create_user(body, db)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "detail": str(e)},
        )


@router.patch("/users/{user_id}", response_model=UserPatchResponse)
async def patch_user(
    user_id: uuid.UUID,
    body: UserPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        if body.is_active:
            user = await UserService.unblock_user(user_id, db)
        else:
            user = await UserService.block_user(user_id, db)
        return user
    except ValueError as e:
        if "not_found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found"},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}/apps", response_model=List[AppAccessItem])
async def get_user_apps(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )
    access = await repo.get_app_access(user_id)
    return access


@router.put("/users/{user_id}/apps", response_model=List[AppAccessItem])
async def put_user_apps(
    user_id: uuid.UUID,
    body: List[AppAccessItem],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )

    provided_apps = {item.app_name for item in body}
    if provided_apps != set(PROTECTED_APPS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_error",
                "detail": "All 8 app entries must be present",
            },
        )

    access = await UserService.update_app_access(user_id, body, db)
    return access
