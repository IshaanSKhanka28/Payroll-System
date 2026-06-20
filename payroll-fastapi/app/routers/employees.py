import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.dependencies.auth import get_current_user, require_role
from app.dependencies.db import get_db
from app.models.employee import Employee, EmployeeStatus
from app.models.salary_component import SalaryComponent
from app.models.user import User, UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    SalaryComponentCreate,
    SalaryComponentResponse,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/employees", tags=["employees"])


from datetime import date, datetime


def serialize_changes(data):
    if isinstance(data, dict):
        return {k: serialize_changes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_changes(v) for v in data]
    elif isinstance(data, Decimal):
        return str(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    elif hasattr(data, "value"):
        return data.value
    elif isinstance(data, uuid.UUID):
        return str(data)
    return data


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    department: str | None = Query(None),
    status: EmployeeStatus | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    query = select(Employee).options(selectinload(Employee.salary_components))
    if department:
        query = query.where(Employee.department == department)
    if status:
        query = query.where(Employee.status == status)
    if search:
        query = query.where(
            or_(
                Employee.name.ilike(f"%{search}%"),
                Employee.designation.ilike(f"%{search}%"),
            )
        )
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{id}", response_model=EmployeeResponse)
async def get_employee(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.salary_components))
        .where(Employee.id == id)
    )
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if (
        current_user.role.value == "EMPLOYEE"
        and current_user.id != employee.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: insufficient permissions",
        )

    return employee


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.employee))
        .where(User.id == employee_data.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee profile already exists for this user",
        )

    employee = Employee(
        user_id=employee_data.user_id,
        name=employee_data.name,
        department=employee_data.department,
        designation=employee_data.designation,
        base_salary=employee_data.base_salary,
        bank_account=employee_data.bank_account,
        ifsc_code=employee_data.ifsc_code,
        status=employee_data.status,
    )
    db.add(employee)
    await db.commit()

    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.salary_components))
        .where(Employee.id == employee.id)
    )
    employee = result.scalars().first()

    changes = serialize_changes(employee_data.model_dump())
    await log_action(
        db=db,
        performed_by=current_user.id,
        action="CREATE",
        entity="employee",
        entity_id=employee.id,
        changes=changes,
    )

    return employee


@router.patch("/{id}", response_model=EmployeeResponse)
async def update_employee(
    id: uuid.UUID,
    employee_data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.salary_components))
        .where(Employee.id == id)
    )
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    update_dict = employee_data.model_dump(exclude_unset=True)
    changes = {}
    for key, val in update_dict.items():
        old_val = getattr(employee, key)
        if old_val != val:
            changes[key] = {
                "old": serialize_changes(old_val),
                "new": serialize_changes(val),
            }
            setattr(employee, key, val)

    if changes:
        await db.commit()

        result = await db.execute(
            select(Employee)
            .options(selectinload(Employee.salary_components))
            .where(Employee.id == id)
        )
        employee = result.scalars().first()

        await log_action(
            db=db,
            performed_by=current_user.id,
            action="UPDATE",
            entity="employee",
            entity_id=employee.id,
            changes=changes,
        )

    return employee


@router.post(
    "/{id}/salary-components",
    response_model=SalaryComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_salary_component(
    id: uuid.UUID,
    component_data: SalaryComponentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    result = await db.execute(select(Employee).where(Employee.id == id))
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    component = SalaryComponent(
        employee_id=id,
        name=component_data.name,
        type=component_data.type,
        amount=component_data.amount,
        is_percentage=component_data.is_percentage,
        effective_from=component_data.effective_from,
        effective_to=component_data.effective_to,
    )
    db.add(component)
    await db.commit()
    await db.refresh(component)

    changes = serialize_changes(component_data.model_dump())
    await log_action(
        db=db,
        performed_by=current_user.id,
        action="ADD_SALARY_COMPONENT",
        entity="salary_component",
        entity_id=component.id,
        changes=changes,
    )

    return component
