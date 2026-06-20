# Antigravity Workspace Rules — Payroll FastAPI Backend

## Project
FinTech payroll backend for an FTC (Fintech Club) selection task.
Evaluated on: backend design, API design, database structure, system thinking. A frontend may be added later but is NOT the priority.

## Stack — do not substitute or "improve" on these
- FastAPI (Python, async)
- PostgreSQL
- SQLAlchemy 2.0 (async engine, async sessions)
- Alembic for migrations
- Pydantic v2 for request/response validation
- python-jose for JWT
- passlib[bcrypt] for password hashing
- pytest for tests

## Non-negotiable design constraints
1. Money fields are always Numeric/Decimal in the DB and in Python (decimal.Decimal). Never float. Floating point rounding errors in payroll calculations are unacceptable.

2. Payroll processing MUST be fault tolerant per-employee, not per-run. If employee 300 of 500 fails during a payroll run, employees 1-299 must remain paid (their PayrollTransaction rows stay SUCCESS), the run's overall status becomes PARTIAL, and only the failed employees should be retryable later — without double-paying anyone who already succeeded. This means: one independent DB transaction per employee inside the payroll loop, never one transaction wrapping the entire batch. If you ever propose wrapping the whole run in a single transaction "for simplicity," stop and flag it to me instead — that is a rejected design, not a shortcut.

3. PayrollRun has a UNIQUE constraint on (month, year). The same month can never be paid twice while a COMPLETED or PARTIAL run exists for it.

4. Two roles only: ADMIN and EMPLOYEE.
   - ADMIN: full access to employee CRUD, triggering payroll, viewing all payslips, audit logs, analytics.
   - EMPLOYEE: can only view their own employee profile, their own salary history, their own payslips, their own notifications. Enforce this at the dependency/query level, not just in the UI.

5. Every state-changing endpoint (POST/PUT/PATCH/DELETE) must write an AuditLog row: who did it, what action, which entity/id, and what changed.

6. Long-running work (the actual payroll distribution loop) must run as a background task. The POST /api/payroll/trigger endpoint returns immediately with the run id and status=PROCESSING — it does not block until all employees are processed.

## Database schema (already finalized — implement exactly this, do not redesign it)
- User(id uuid pk, email unique, password_hash, role enum[ADMIN,EMPLOYEE], created_at, updated_at)
- Employee(id uuid pk, user_id fk unique, name, department, designation, base_salary numeric(12,2), bank_account, ifsc_code, status enum[ACTIVE,INACTIVE,ON_LEAVE], joined_at, updated_at)
- PayrollRun(id uuid pk, initiated_by fk, month int, year int, status enum[PENDING,PROCESSING,COMPLETED,FAILED,PARTIAL], total_amount numeric(14,2), employee_count int, initiated_at, completed_at nullable, UNIQUE(month, year))
- PayrollTransaction(id uuid pk, payroll_run_id fk, employee_id fk, gross_salary numeric(12,2), deductions numeric(12,2), net_salary numeric(12,2), status enum[PENDING,SUCCESS,FAILED], failure_reason nullable, processed_at nullable)
- SalaryComponent(id uuid pk, employee_id fk, name, type enum[ALLOWANCE,DEDUCTION], amount numeric(10,2), is_percentage bool default false, effective_from date, effective_to date nullable)
- AuditLog(id uuid pk, performed_by fk, action, entity, entity_id, changes jsonb nullable, created_at)
- Notification(id uuid pk, user_id fk, type enum[PAYROLL_INITIATED,PAYROLL_CREDITED,PAYROLL_FAILED,SALARY_REVISED], title, message, is_read bool default false, sent_at)

## Folder structure — implement exactly this
payroll-fastapi/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/          (one file per table)
│   ├── schemas/          (Pydantic models)
│   ├── routers/          (one APIRouter per domain)
│   ├── services/         (business logic, no FastAPI imports)
│   ├── dependencies/     (get_current_user, require_role, get_db)
│   └── utils/            (security.py, logger.py)
├── alembic/
├── tests/
├── .env.example
├── requirements.txt
└── README.md

## Working style
- Before writing code for a new domain (auth, employees, payroll, reports, notifications), produce a short plan artifact first and wait for my review on it before implementing.
- After implementing the payroll trigger + processing logic specifically, write the test described in my task prompt and run it yourself using the browser/terminal subagent — show me the actual pass/fail output, don't just claim it works.
- Explain non-obvious decisions in code comments — I need to be able to explain this system in an interview, so the comments should teach, not just describe.
