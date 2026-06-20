import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    performed_by: uuid.UUID
    action: str
    entity: str
    entity_id: str
    changes: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PayslipComponent(BaseModel):
    name: str
    type: str
    amount: Decimal
    is_percentage: bool

class PayslipResponse(BaseModel):
    payslip_number: str
    employee_id: uuid.UUID
    employee_name: str
    department: str
    designation: str
    bank_account: str
    ifsc_code: str
    month: int
    year: int
    gross_salary: Decimal
    deductions: Decimal
    net_salary: Decimal
    status: str
    processed_at: datetime | None = None
    itemized_components: list[PayslipComponent] = []

    model_config = ConfigDict(from_attributes=True)

class MonthlyPayout(BaseModel):
    year: int
    month: int
    total_amount: Decimal
    employee_count: int

class DepartmentBreakdown(BaseModel):
    department: str
    headcount: int
    avg_salary: Decimal
    total_cost: Decimal

class OverallStats(BaseModel):
    active_employees: int
    total_payouts_this_year: Decimal
    failed_transaction_count: int

class AnalyticsResponse(BaseModel):
    monthly_payouts: list[MonthlyPayout]
    department_breakdown: list[DepartmentBreakdown]
    overall_stats: OverallStats
