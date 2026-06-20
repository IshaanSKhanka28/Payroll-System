from decimal import Decimal
from app.services.payroll_service import calculate_net_salary
from app.models.salary_component import SalaryComponentType

class MockEmployee:
    def __init__(self, base_salary: Decimal):
        self.base_salary = base_salary

class MockSalaryComponent:
    def __init__(self, name: str, type: SalaryComponentType, amount: Decimal, is_percentage: bool):
        self.name = name
        self.type = type
        self.amount = amount
        self.is_percentage = is_percentage

def test_base_only():
    employee = MockEmployee(Decimal("50000.00"))
    components = []
    res = calculate_net_salary(employee, components)
    assert res["gross_salary"] == Decimal("50000.00")
    assert res["deductions"] == Decimal("0.00")
    assert res["net_salary"] == Decimal("50000.00")

def test_fixed_allowance():
    employee = MockEmployee(Decimal("50000.00"))
    components = [
        MockSalaryComponent("Allowance 1", SalaryComponentType.ALLOWANCE, Decimal("5000.00"), False)
    ]
    res = calculate_net_salary(employee, components)
    assert res["gross_salary"] == Decimal("55000.00")
    assert res["deductions"] == Decimal("0.00")
    assert res["net_salary"] == Decimal("55000.00")

def test_percentage_deduction():
    employee = MockEmployee(Decimal("50000.00"))
    components = [
        MockSalaryComponent("Deduction 1", SalaryComponentType.DEDUCTION, Decimal("10.00"), True)
    ]
    res = calculate_net_salary(employee, components)
    assert res["gross_salary"] == Decimal("50000.00")
    assert res["deductions"] == Decimal("5000.00")
    assert res["net_salary"] == Decimal("45000.00")

def test_mixed_components():
    employee = MockEmployee(Decimal("75000.00"))
    components = [
        MockSalaryComponent("HRA", SalaryComponentType.ALLOWANCE, Decimal("40.00"), True),
        MockSalaryComponent("Bonus", SalaryComponentType.ALLOWANCE, Decimal("5000.00"), False),
        MockSalaryComponent("PF", SalaryComponentType.DEDUCTION, Decimal("12.00"), True),
        MockSalaryComponent("Tax", SalaryComponentType.DEDUCTION, Decimal("2000.00"), False),
    ]
    res = calculate_net_salary(employee, components)
    assert res["gross_salary"] == Decimal("110000.00")
    assert res["deductions"] == Decimal("11000.00")
    assert res["net_salary"] == Decimal("99000.00")

def test_net_never_negative():
    employee = MockEmployee(Decimal("10000.00"))
    components = [
        MockSalaryComponent("PF", SalaryComponentType.DEDUCTION, Decimal("120.00"), True)
    ]
    res = calculate_net_salary(employee, components)
    assert res["gross_salary"] == Decimal("10000.00")
    assert res["deductions"] == Decimal("12000.00")
    assert res["net_salary"] == Decimal("0.00")
