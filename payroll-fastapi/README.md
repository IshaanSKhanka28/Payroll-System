# Payroll FastAPI Backend

A robust, fault-tolerant Fintech payroll backend built using FastAPI, PostgreSQL, and SQLAlchemy 2.0.

---

## Architecture & System Design

### Fault-Tolerant Payroll Distribution
Payroll calculations and payouts are processed on a **per-employee transaction isolation** model rather than wrapping the entire batch in a single database transaction. This ensures high fault tolerance and recovery:

1. **Per-Employee Isolation**: Each employee's net salary calculation, transaction logging (`PayrollTransaction`), and notification creation occur inside their own dedicated database session and transaction.
2. **Resilience to Failures**: If employee 300 of 500 fails (e.g. database locks, invalid profile configurations, or calculation errors), their transaction is rolled back individually and logged as `FAILED` (generating a `PAYROLL_FAILED` notification). Employees 1 to 299 remain paid, and their status stays `SUCCESS` in the database.
3. **Run Aggregation**: Once the batch loop completes, the overarching `PayrollRun` status is set to:
   - `COMPLETED`: If all transactions succeeded.
   - `FAILED`: If all transactions failed.
   - `PARTIAL`: If there was a mix of successful and failed distributions.
4. **Double-Payment Prevention**: The database enforces a `UNIQUE(month, year)` constraint on `PayrollRun`. Once a run in status `COMPLETED`, `PARTIAL`, or `PROCESSING` exists for a month, new trigger attempts are rejected.
5. **Retry Logic**: Admin users can call the `/api/payroll/runs/{id}/retry` endpoint. This deletes only the `FAILED` transactions of that run, and re-triggers the processing loop exclusively for those failed employees. It aggregates the final payouts and updates the overall status of the original run to `COMPLETED` once all succeed.

---

## Local Setup & Installation

### Prerequisites
- Python 3.13+
- PostgreSQL (or SQLite for local testing)

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/IshaanSKhanka28/Payroll-System.git
   cd Payroll-System/payroll-fastapi
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file (copied from `.env.example`):
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/payroll
   JWT_SECRET_KEY=supersecretkey123
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

4. **Initialize Database and Apply Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Run the Database Seeding Script**:
   This seeds 1 Admin account and 5 Employees with varied base salaries, plus HRA Allowance (40%) and PF Deduction (12%) components.
   ```bash
   python seed.py
   ```

6. **Start the Development Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Running Verification Suites

### Running Unit Tests
We use `pytest` to run our unit test suite covering net salary calculations, allowances, deductions, and rounding rules:
```bash
python -m pytest
```

### Running E2E Verification
You can run the end-to-end verification script locally to spin up a mock SQLite database, seed it, trigger a payroll run, and verify that Employee A gets exactly ₹96,000 net:
```bash
python verify_e2e.py
```

> [!NOTE]  
> **FOLLOW-UP (PostgreSQL E2E Verification)**:  
> To run the E2E verification against a live PostgreSQL instance prior to the final demo, run:
> ```bash
> $env:DATABASE_URL="postgresql+asyncpg://<username>:<password>@<host>:<port>/<dbname>"; python seed.py
> $env:DATABASE_URL="postgresql+asyncpg://<username>:<password>@<host>:<port>/<dbname>"; python -m uvicorn app.main:app --port 8000
> python verify_e2e.py
> ```

---

## API Endpoints & Usage

### 1. Authentication Router
#### Register User (Public)
`POST /api/auth/register`
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "boss@example.com", "password": "password123", "role": "ADMIN"}'
```

#### Login (Public)
`POST /api/auth/login`
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "boss@example.com", "password": "password123"}'
```

#### Fetch Current Profile (Protected)
`GET /api/auth/me`
```bash
curl -X GET http://127.0.0.1:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

### 2. Employees Router
#### List Employees (ADMIN only, Paginated & Filterable)
`GET /api/employees?page=1&limit=10&department=Engineering`
```bash
curl -X GET "http://127.0.0.1:8000/api/employees?page=1&limit=10" \
  -H "Authorization: Bearer <admin_token>"
```

#### Fetch Profile (ADMIN, or Owner EMPLOYEE)
`GET /api/employees/{id}`
```bash
curl -X GET http://127.0.0.1:8000/api/employees/<employee_id> \
  -H "Authorization: Bearer <token>"
```

#### Create Employee Profile (ADMIN only)
`POST /api/employees`
```bash
curl -X POST http://127.0.0.1:8000/api/employees \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"user_id": "<user_uuid>", "name": "Jane Doe", "department": "HR", "designation": "Manager", "base_salary": "60000.00", "bank_account": "987654321098", "ifsc_code": "HDFC0001234", "status": "ACTIVE"}'
```

#### Partially Update Profile (ADMIN only)
`PATCH /api/employees/{id}`
```bash
curl -X PATCH http://127.0.0.1:8000/api/employees/<employee_id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"department": "Operations", "base_salary": "65000.00"}'
```

#### Add Salary Component (ADMIN only)
`POST /api/employees/{id}/salary-components`
```bash
curl -X POST http://127.0.0.1:8000/api/employees/<employee_id>/salary-components \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"name": "HRA", "type": "ALLOWANCE", "amount": "40.00", "is_percentage": true, "effective_from": "2026-04-01"}'
```

---

### 3. Payroll Router
#### Trigger Payroll Run (ADMIN only)
`POST /api/payroll/trigger`
```bash
curl -X POST http://127.0.0.1:8000/api/payroll/trigger \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"month": 6, "year": 2026}'
```

#### Retry Failed Transactions (ADMIN only)
`POST /api/payroll/runs/{id}/retry`
```bash
curl -X POST http://127.0.0.1:8000/api/payroll/runs/<run_uuid>/retry \
  -H "Authorization: Bearer <admin_token>"
```

#### View My Salary History (EMPLOYEE only)
`GET /api/payroll/my-transactions`
```bash
curl -X GET http://127.0.0.1:8000/api/payroll/my-transactions \
  -H "Authorization: Bearer <employee_token>"
```

---

### 4. Reports & Analytics Router
#### View System Audit Logs (ADMIN only, Paginated & Filterable)
`GET /api/reports/audit-log`
```bash
curl -X GET "http://127.0.0.1:8000/api/reports/audit-log?page=1&limit=10" \
  -H "Authorization: Bearer <admin_token>"
```

#### Fetch Payslip (ADMIN, or Owner EMPLOYEE)
`GET /api/reports/payslip/{transaction_id}`
```bash
curl -X GET http://127.0.0.1:8000/api/reports/payslip/<transaction_uuid> \
  -H "Authorization: Bearer <token>"
```

#### Fetch Financial Analytics (ADMIN only)
`GET /api/reports/analytics?financial_year=2026`
```bash
curl -X GET "http://127.0.0.1:8000/api/reports/analytics?financial_year=2026" \
  -H "Authorization: Bearer <admin_token>"
```

---

### 5. Notifications Router
#### List User Notifications (Protected)
`GET /api/notifications`
```bash
curl -X GET http://127.0.0.1:8000/api/notifications \
  -H "Authorization: Bearer <token>"
```

#### Mark Notifications as Read (Protected)
`PATCH /api/notifications/read`
```bash
curl -X PATCH http://127.0.0.1:8000/api/notifications/read \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"notification_id": "<notification_uuid>"}'
```

#### Broadcast Notification (ADMIN only)
`POST /api/notifications/broadcast`
```bash
curl -X POST http://127.0.0.1:8000/api/notifications/broadcast \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"type": "SALARY_REVISED", "title": "System Announcement", "message": "Broadcast alert details."}'
```
