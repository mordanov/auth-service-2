import uuid
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from db.database import Base


PROTECTED_APPS = [
    "budget-site",
    "family-admin-routine",
    "family-archive",
    "family-kitchen-recipes",
    "new-site",
    "portuguese-expenses",
    "reminders-app",
    "servinga-dashboard",
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    app_access: Mapped[list["UserAppAccess"]] = relationship(
        "UserAppAccess", back_populates="user", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["AuthToken"]] = relationship(  # type: ignore[name-defined]
        "AuthToken", back_populates="user", cascade="all, delete-orphan"
    )


class UserAppAccess(Base):
    __tablename__ = "user_app_access"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="app_access")

    __table_args__ = (UniqueConstraint("user_id", "app_name", name="uq_user_app"),)
