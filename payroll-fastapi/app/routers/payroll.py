import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.dependencies.auth import require_role, get_current_user
from app.dependencies.db import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import PayrollRun, PayrollTransaction
from app.schemas.payroll import (
    PayrollTriggerRequest,
    PayrollRunResponse,
    PayrollRunDetailResponse,
    PayrollTransactionResponse,
)
from app.services.payroll_service import trigger_payroll_run, retry_failed_transactions

router = APIRouter(prefix="/api/payroll", tags=["payroll"])

@router.post("/trigger", response_model=PayrollRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_run(
    payload: PayrollTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    return await trigger_payroll_run(
        db=db,
        month=payload.month,
        year=payload.year,
        admin_user_id=current_user.id,
        background_tasks=background_tasks,
    )

@router.get("/runs", response_model=list[PayrollRunResponse])
async def list_runs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(
        select(PayrollRun)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/runs/{id}", response_model=PayrollRunDetailResponse)
async def get_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(
        select(PayrollRun)
        .options(selectinload(PayrollRun.transactions))
        .where(PayrollRun.id == id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found"
        )
    return run

@router.post("/runs/{id}/retry", response_model=PayrollRunResponse)
async def retry_run(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    return await retry_failed_transactions(
        db=db,
        run_id=id,
        background_tasks=background_tasks,
    )

@router.get("/my-transactions", response_model=list[PayrollTransactionResponse])
async def my_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found for the current user"
        )
    tx_result = await db.execute(
        select(PayrollTransaction).where(PayrollTransaction.employee_id == employee.id)
    )
    return tx_result.scalars().all()
