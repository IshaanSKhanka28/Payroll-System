"""SQLAlchemy Employee model definition."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EmployeeStatus(str, enum.Enum):
    """Employee status enumeration specifying whether an employee is active, inactive, or on leave."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"


class Employee(Base):
    """Employee model representing an employee profile and their salary details."""

    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    # base_salary uses Numeric(12, 2) and decimal.Decimal to prevent floating point issues.
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bank_account: Mapped[str] = mapped_column(String(50), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="employee_status_enum"),
        default=EmployeeStatus.ACTIVE,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="employee")
    salary_components: Mapped[list["SalaryComponent"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    payroll_transactions: Mapped[list["PayrollTransaction"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
