import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.payroll import PayrollRunStatus, PayrollTransactionStatus

class PayrollTriggerRequest(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000)

class PayrollTransactionResponse(BaseModel):
    id: uuid.UUID
    payroll_run_id: uuid.UUID
    employee_id: uuid.UUID
    gross_salary: Decimal
    deductions: Decimal
    net_salary: Decimal
    status: PayrollTransactionStatus
    failure_reason: str | None = None
    processed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class PayrollRunResponse(BaseModel):
    id: uuid.UUID
    initiated_by: uuid.UUID
    month: int
    year: int
    status: PayrollRunStatus
    total_amount: Decimal
    employee_count: int
    initiated_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class PayrollRunDetailResponse(PayrollRunResponse):
    transactions: list[PayrollTransactionResponse] = []

    model_config = ConfigDict(from_attributes=True)
