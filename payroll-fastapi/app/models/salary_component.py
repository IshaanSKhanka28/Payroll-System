"""SQLAlchemy SalaryComponent model definition."""

import enum
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SalaryComponentType(str, enum.Enum):
    """Type enumeration for a salary component indicating an addition or subtraction."""

    ALLOWANCE = "ALLOWANCE"
    DEDUCTION = "DEDUCTION"


class SalaryComponent(Base):
    """SalaryComponent model storing base salary adjustments (allowances and deductions)."""

    __tablename__ = "salary_components"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[SalaryComponentType] = mapped_column(
        Enum(SalaryComponentType, name="salary_component_type_enum"),
        nullable=False,
    )
    # Component amount (either currency or percentage)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_percentage: Mapped[bool] = mapped_column(default=False, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=True)

    # Relationships
    employee: Mapped["Employee"] = relationship(
        back_populates="salary_components"
    )
