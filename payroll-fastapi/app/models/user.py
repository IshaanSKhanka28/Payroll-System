"""SQLAlchemy User model definition."""

import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration defining two core roles: ADMIN and EMPLOYEE."""

    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"


class User(Base):
    """User model representing authentication and credential details."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # One-to-One: A user optionally has an associated employee profile.
    # We use cascade to delete the employee profile if the user is deleted.
    employee: Mapped["Employee"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-Many: Logs of actions performed by this user
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
