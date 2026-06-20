import asyncio
from decimal import Decimal
from datetime import date
from sqlalchemy.future import select
from app.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.employee import Employee, EmployeeStatus
from app.models.salary_component import SalaryComponent, SalaryComponentType
from app.utils.security import hash_password

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(select(User).where(User.email == "admin@example.com"))
            admin = res.scalars().first()
            if not admin:
                admin = User(
                    email="admin@example.com",
                    password_hash=hash_password("adminpassword123"),
                    role=UserRole.ADMIN
                )
                session.add(admin)

            employees_data = [
                {"email": "empa@example.com", "name": "Employee A", "dept": "Engineering", "desig": "Developer", "salary": "75000.00"},
                {"email": "empb@example.com", "name": "Employee B", "dept": "Sales", "desig": "Representative", "salary": "90000.00"},
                {"email": "empc@example.com", "name": "Employee C", "dept": "Marketing", "desig": "Specialist", "salary": "50000.00"},
                {"email": "empd@example.com", "name": "Employee D", "dept": "HR", "desig": "Generalist", "salary": "65000.00"},
                {"email": "empe@example.com", "name": "Employee E", "dept": "Operations", "desig": "Coordinator", "salary": "95000.00"},
            ]

            for emp in employees_data:
                res_user = await session.execute(select(User).where(User.email == emp["email"]))
                user = res_user.scalars().first()
                if not user:
                    user = User(
                        email=emp["email"],
                        password_hash=hash_password(f"emppass{emp['email'][3]}"),
                        role=UserRole.EMPLOYEE
                    )
                    session.add(user)
                    await session.flush()

                res_profile = await session.execute(select(Employee).where(Employee.user_id == user.id))
                profile = res_profile.scalars().first()
                if not profile:
                    profile = Employee(
                        user_id=user.id,
                        name=emp["name"],
                        department=emp["dept"],
                        designation=emp["desig"],
                        base_salary=Decimal(emp["salary"]),
                        bank_account="123456789" + str(employees_data.index(emp)),
                        ifsc_code="SBIN0001234",
                        status=EmployeeStatus.ACTIVE
                    )
                    session.add(profile)
                    await session.flush()

                    hra = SalaryComponent(
                        employee_id=profile.id,
                        name="HRA",
                        type=SalaryComponentType.ALLOWANCE,
                        amount=Decimal("40.00"),
                        is_percentage=True,
                        effective_from=date(2026, 4, 1)
                    )
                    pf = SalaryComponent(
                        employee_id=profile.id,
                        name="PF",
                        type=SalaryComponentType.DEDUCTION,
                        amount=Decimal("12.00"),
                        is_percentage=True,
                        effective_from=date(2026, 4, 1)
                    )
                    session.add(hra)
                    session.add(pf)

if __name__ == "__main__":
    asyncio.run(seed_data())
