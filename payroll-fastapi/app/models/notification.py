"""SQLAlchemy Notification model definition."""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NotificationType(str, enum.Enum):
    """Type enumeration for notifications defining system/payroll events."""

    PAYROLL_INITIATED = "PAYROLL_INITIATED"
    PAYROLL_CREDITED = "PAYROLL_CREDITED"
    PAYROLL_FAILED = "PAYROLL_FAILED"
    SALARY_REVISED = "SALARY_REVISED"


class Notification(Base):
    """Notification model storing user alerts about payroll and system actions."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    # Many-to-One: The recipient User of the notification
    user: Mapped["User"] = relationship()
