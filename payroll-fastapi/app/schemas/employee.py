import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.employee import EmployeeStatus
from app.models.salary_component import SalaryComponentType


class SalaryComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: SalaryComponentType
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    is_percentage: bool = False
    effective_from: date
    effective_to: date | None = None


class SalaryComponentResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    name: str
    type: SalaryComponentType
    amount: Decimal
    is_percentage: bool
    effective_from: date
    effective_to: date | None

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    user_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=100)
    designation: str = Field(..., min_length=1, max_length=100)
    base_salary: Decimal = Field(..., gt=Decimal("0.00"))
    bank_account: str = Field(
        ..., min_length=9, max_length=18, pattern="^[a-zA-Z0-9]+$"
    )
    ifsc_code: str = Field(..., pattern="^[A-Z]{4}0[A-Z0-9]{6}$")
    status: EmployeeStatus = EmployeeStatus.ACTIVE


class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    department: str | None = Field(None, min_length=1, max_length=100)
    designation: str | None = Field(None, min_length=1, max_length=100)
    base_salary: Decimal | None = Field(None, gt=Decimal("0.00"))
    bank_account: str | None = Field(
        None, min_length=9, max_length=18, pattern="^[a-zA-Z0-9]+$"
    )
    ifsc_code: str | None = Field(None, pattern="^[A-Z]{4}0[A-Z0-9]{6}$")
    status: EmployeeStatus | None = None


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    department: str
    designation: str
    base_salary: Decimal
    bank_account: str
    ifsc_code: str
    status: EmployeeStatus
    joined_at: datetime
    updated_at: datetime
    salary_components: list[SalaryComponentResponse] = []

    model_config = ConfigDict(from_attributes=True)
