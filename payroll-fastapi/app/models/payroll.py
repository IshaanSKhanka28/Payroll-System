"""SQLAlchemy PayrollRun and PayrollTransaction models definition."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PayrollRunStatus(str, enum.Enum):
    """Status enumeration for a payroll run batch."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class PayrollTransactionStatus(str, enum.Enum):
    """Status enumeration for a single employee's payroll transaction."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PayrollRun(Base):
    """PayrollRun model tracking execution status and aggregates of salary runs."""

    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_payroll_runs_month_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PayrollRunStatus] = mapped_column(
        Enum(PayrollRunStatus, name="payroll_run_status_enum"),
        default=PayrollRunStatus.PENDING,
        nullable=False,
    )
    # Total net salary disbursed in this run
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Headcount processed in this run
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    # Many-to-One: The Admin user who triggered the run
    creator: Mapped["User"] = relationship()
    # One-to-Many: Transactions spawned under this run
    transactions: Mapped[list["PayrollTransaction"]] = relationship(
        back_populates="payroll_run", cascade="all, delete-orphan"
    )


class PayrollTransaction(Base):
    """PayrollTransaction model recording individual employee salary distributions."""

    __tablename__ = "payroll_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payroll_runs.id"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id"), nullable=False
    )
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PayrollTransactionStatus] = mapped_column(
        Enum(PayrollTransactionStatus, name="payroll_transaction_status_enum"),
        default=PayrollTransactionStatus.PENDING,
        nullable=False,
    )
    failure_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    payroll_run: Mapped["PayrollRun"] = relationship(
        back_populates="transactions"
    )
    employee: Mapped["Employee"] = relationship(
        back_populates="payroll_transactions"
    )
