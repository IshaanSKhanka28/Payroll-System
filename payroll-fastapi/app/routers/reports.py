import uuid
import calendar
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.dependencies.auth import require_role, get_current_user
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.models.employee import Employee, EmployeeStatus
from app.models.payroll import PayrollRun, PayrollTransaction, PayrollRunStatus, PayrollTransactionStatus
from app.models.audit_log import AuditLog
from app.models.salary_component import SalaryComponent
from app.schemas.reports import (
    AuditLogResponse,
    PayslipResponse,
    PayslipComponent,
    AnalyticsResponse,
    MonthlyPayout,
    DepartmentBreakdown,
    OverallStats,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/audit-log", response_model=list[AuditLogResponse])
async def get_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    action: str | None = Query(None),
    entity: str | None = Query(None),
    performed_by: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity == entity)
    if performed_by:
        query = query.where(AuditLog.performed_by == performed_by)
    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/payslip/{transaction_id}", response_model=PayslipResponse)
async def get_payslip(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(PayrollTransaction)
        .options(
            selectinload(PayrollTransaction.employee),
            selectinload(PayrollTransaction.payroll_run),
        )
        .where(PayrollTransaction.id == transaction_id)
    )
    tx = res.scalars().first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    employee = tx.employee
    run = tx.payroll_run
    if current_user.role == UserRole.EMPLOYEE and employee.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: insufficient permissions"
        )
    bank_account = employee.bank_account
    if len(bank_account) >= 4:
        masked_account = "*" * (len(bank_account) - 4) + bank_account[-4:]
    else:
        masked_account = bank_account
    first_day = date(run.year, run.month, 1)
    last_day = date(run.year, run.month, calendar.monthrange(run.year, run.month)[1])
    comp_res = await db.execute(
        select(SalaryComponent).where(
            SalaryComponent.employee_id == employee.id,
            SalaryComponent.effective_from <= last_day,
            or_(SalaryComponent.effective_to.is_(None), SalaryComponent.effective_to >= first_day)
        )
    )
    components = comp_res.scalars().all()
    itemized = [
        PayslipComponent(
            name=c.name,
            type=c.type.value,
            amount=c.amount,
            is_percentage=c.is_percentage
        )
        for c in components
    ]
    payslip_number = f"PAY-{run.year}-{run.month:02d}-{str(tx.id)[:8]}"
    return PayslipResponse(
        payslip_number=payslip_number,
        employee_id=employee.id,
        employee_name=employee.name,
        department=employee.department,
        designation=employee.designation,
        bank_account=masked_account,
        ifsc_code=employee.ifsc_code,
        month=run.month,
        year=run.year,
        gross_salary=tx.gross_salary,
        deductions=tx.deductions,
        net_salary=tx.net_salary,
        status=tx.status.value,
        processed_at=tx.processed_at,
        itemized_components=itemized
    )

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    financial_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    if financial_year is None:
        now = datetime.now()
        if now.month >= 4:
            financial_year = now.year
        else:
            financial_year = now.year - 1
    fy_filter = or_(
        and_(PayrollRun.year == financial_year, PayrollRun.month >= 4),
        and_(PayrollRun.year == financial_year + 1, PayrollRun.month <= 3)
    )
    runs_res = await db.execute(
        select(
            PayrollRun.year,
            PayrollRun.month,
            func.sum(PayrollRun.total_amount).label("total_amount"),
            func.sum(PayrollRun.employee_count).label("employee_count")
        )
        .where(
            PayrollRun.status.in_([PayrollRunStatus.COMPLETED, PayrollRunStatus.PARTIAL]),
            fy_filter
        )
        .group_by(PayrollRun.year, PayrollRun.month)
        .order_by(PayrollRun.year, PayrollRun.month)
    )
    monthly_payouts = [
        MonthlyPayout(
            year=row.year,
            month=row.month,
            total_amount=row.total_amount,
            employee_count=row.employee_count
        )
        for row in runs_res.all()
    ]
    dept_res = await db.execute(
        select(
            Employee.department,
            func.count(Employee.id).label("headcount"),
            func.avg(Employee.base_salary).label("avg_salary"),
            func.sum(Employee.base_salary).label("total_cost")
        )
        .where(Employee.status == EmployeeStatus.ACTIVE)
        .group_by(Employee.department)
    )
    department_breakdown = [
        DepartmentBreakdown(
            department=row.department,
            headcount=row.headcount,
            avg_salary=Decimal(str(row.avg_salary)).quantize(Decimal("0.01")),
            total_cost=row.total_cost
        )
        for row in dept_res.all()
    ]
    active_count_res = await db.execute(
        select(func.count(Employee.id)).where(Employee.status == EmployeeStatus.ACTIVE)
    )
    active_count = active_count_res.scalar() or 0
    payout_sum_res = await db.execute(
        select(func.sum(PayrollRun.total_amount))
        .where(
            PayrollRun.status.in_([PayrollRunStatus.COMPLETED, PayrollRunStatus.PARTIAL]),
            fy_filter
        )
    )
    total_payouts = payout_sum_res.scalar() or Decimal("0.00")
    failed_count_res = await db.execute(
        select(func.count(PayrollTransaction.id))
        .join(PayrollRun)
        .where(
            PayrollTransaction.status == PayrollTransactionStatus.FAILED,
            fy_filter
        )
    )
    failed_count = failed_count_res.scalar() or 0
    return AnalyticsResponse(
        monthly_payouts=monthly_payouts,
        department_breakdown=department_breakdown,
        overall_stats=OverallStats(
            active_employees=active_count,
            total_payouts_this_year=total_payouts,
            failed_transaction_count=failed_count
        )
    )
