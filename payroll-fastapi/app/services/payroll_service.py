import uuid
import calendar
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.payroll import PayrollRun, PayrollRunStatus, PayrollTransaction, PayrollTransactionStatus
from app.models.employee import Employee, EmployeeStatus
from app.models.salary_component import SalaryComponentType
from app.models.notification import Notification, NotificationType
from app.database import AsyncSessionLocal

def calculate_net_salary(employee, salary_components) -> dict:
    base = employee.base_salary
    gross = base
    deductions = Decimal("0.00")
    for comp in salary_components:
        amount = comp.amount
        if comp.is_percentage:
            comp_amount = base * (amount / Decimal("100.00"))
        else:
            comp_amount = amount
        if comp.type == SalaryComponentType.ALLOWANCE:
            gross += comp_amount
        elif comp.type == SalaryComponentType.DEDUCTION:
            deductions += comp_amount
    net = gross - deductions
    if net < Decimal("0.00"):
        net = Decimal("0.00")
    gross = gross.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    deductions = deductions.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "gross_salary": gross,
        "deductions": deductions,
        "net_salary": net
    }

async def trigger_payroll_run(db, month, year, admin_user_id, background_tasks):
    result = await db.execute(
        select(PayrollRun).where(PayrollRun.month == month, PayrollRun.year == year)
    )
    existing_run = result.scalars().first()
    if existing_run:
        if existing_run.status in (PayrollRunStatus.COMPLETED, PayrollRunStatus.PARTIAL, PayrollRunStatus.PROCESSING):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payroll run already exists or is in progress for this month and year"
            )
        if existing_run.status == PayrollRunStatus.FAILED:
            await db.delete(existing_run)
            await db.commit()
    result = await db.execute(
        select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
    )
    employees = result.scalars().all()
    if not employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active employees found to trigger payroll"
        )
    payroll_run = PayrollRun(
        initiated_by=admin_user_id,
        month=month,
        year=year,
        status=PayrollRunStatus.PROCESSING,
        total_amount=Decimal("0.00"),
        employee_count=len(employees)
    )
    db.add(payroll_run)
    await db.commit()
    await db.refresh(payroll_run)
    employee_ids = [emp.id for emp in employees]
    background_tasks.add_task(
        process_transactions,
        payroll_run.id,
        employee_ids
    )
    return payroll_run

async def process_transactions(run_id: uuid.UUID, employee_ids: list[uuid.UUID]):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PayrollRun).where(PayrollRun.id == run_id)
        )
        run = result.scalars().first()
        if not run:
            return
        month = run.month
        year = run.year
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    for emp_id in employee_ids:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    result = await session.execute(
                        select(Employee)
                        .options(selectinload(Employee.salary_components))
                        .where(Employee.id == emp_id)
                    )
                    employee = result.scalars().first()
                    if not employee:
                        raise ValueError(f"Employee {emp_id} not found")
                    effective_comps = []
                    for comp in employee.salary_components:
                        if comp.effective_from <= last_day and (comp.effective_to is None or comp.effective_to >= first_day):
                            effective_comps.append(comp)
                    sal_details = calculate_net_salary(employee, effective_comps)
                    tx = PayrollTransaction(
                        payroll_run_id=run_id,
                        employee_id=emp_id,
                        gross_salary=sal_details["gross_salary"],
                        deductions=sal_details["deductions"],
                        net_salary=sal_details["net_salary"],
                        status=PayrollTransactionStatus.SUCCESS,
                        processed_at=func.now()
                    )
                    session.add(tx)
                    notif = Notification(
                        user_id=employee.user_id,
                        type=NotificationType.PAYROLL_CREDITED,
                        title="Salary Credited",
                        message=f"Your salary of Net: {sal_details['net_salary']} has been credited."
                    )
                    session.add(notif)
        except Exception as e:
            try:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        result = await session.execute(
                            select(Employee).where(Employee.id == emp_id)
                        )
                        employee = result.scalars().first()
                        tx = PayrollTransaction(
                            payroll_run_id=run_id,
                            employee_id=emp_id,
                            gross_salary=Decimal("0.00"),
                            deductions=Decimal("0.00"),
                            net_salary=Decimal("0.00"),
                            status=PayrollTransactionStatus.FAILED,
                            failure_reason=str(e),
                            processed_at=func.now()
                        )
                        session.add(tx)
                        if employee:
                            notif = Notification(
                                user_id=employee.user_id,
                                type=NotificationType.PAYROLL_FAILED,
                                title="Salary Processing Failed",
                                message=f"Your salary processing failed. Reason: {str(e)}"
                            )
                            session.add(notif)
            except Exception:
                pass
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(PayrollRun).where(PayrollRun.id == run_id)
            )
            run = result.scalars().first()
            if run:
                tx_result = await session.execute(
                    select(PayrollTransaction).where(PayrollTransaction.payroll_run_id == run_id)
                )
                transactions = tx_result.scalars().all()
                success_txs = [t for t in transactions if t.status == PayrollTransactionStatus.SUCCESS]
                failed_txs = [t for t in transactions if t.status == PayrollTransactionStatus.FAILED]
                run.total_amount = sum(t.net_salary for t in success_txs)
                run.employee_count = len(success_txs)
                if len(success_txs) == len(transactions):
                    run.status = PayrollRunStatus.COMPLETED
                elif len(failed_txs) == len(transactions):
                    run.status = PayrollRunStatus.FAILED
                else:
                    run.status = PayrollRunStatus.PARTIAL
                run.completed_at = func.now()

async def retry_failed_transactions(db, run_id, background_tasks):
    result = await db.execute(
        select(PayrollRun).where(PayrollRun.id == run_id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found"
        )
    if run.status not in (PayrollRunStatus.FAILED, PayrollRunStatus.PARTIAL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or partial runs can be retried"
        )
    result = await db.execute(
        select(PayrollTransaction).where(
            PayrollTransaction.payroll_run_id == run_id,
            PayrollTransaction.status == PayrollTransactionStatus.FAILED
        )
    )
    failed_txs = result.scalars().all()
    if not failed_txs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No failed transactions found for this run"
        )
    failed_employee_ids = [tx.employee_id for tx in failed_txs]
    for tx in failed_txs:
        await db.delete(tx)
    run.status = PayrollRunStatus.PROCESSING
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(
        process_transactions,
        run.id,
        failed_employee_ids
    )
    return run
