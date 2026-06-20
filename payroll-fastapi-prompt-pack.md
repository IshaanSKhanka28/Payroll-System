# PROMPT PACK — FastAPI Payroll Backend
# How to use: open this project folder in your terminal, run `claude`,
# then paste prompts ONE AT A TIME in this order. Review each diff before
# moving to the next prompt. Do not paste all of them at once.

═══════════════════════════════════════════════════════════════
PROMPT 0 — Project context (paste this first, always)
═══════════════════════════════════════════════════════════════

I'm building a FinTech payroll backend for an FTC (Fintech Club) selection
task. It will be evaluated on: backend design, API design, database
structure, and system thinking — NOT on having a frontend.

Stack: FastAPI, PostgreSQL, SQLAlchemy (async), Alembic for migrations,
Pydantic v2 for validation, python-jose for JWT, passlib[bcrypt] for
password hashing.

Core requirement: two roles, ADMIN and EMPLOYEE. Admin can trigger a
payroll run that calculates and "pays" (simulated) every active
employee's salary. Employee salaries are stored in the DB with optional
salary components (allowances/deductions, fixed or percentage-based).

Critical constraint: payroll processing must be FAULT TOLERANT. If
employee 300 of 500 fails during a payroll run, employees 1-299 must
stay paid, the run status must reflect PARTIAL completion, and failed
employees must be individually retryable — without double-paying anyone
who already succeeded. Use one DB transaction per employee, not one
giant transaction for the whole run.

I'll give you the schema design next. Do not start writing code yet —
just confirm you understand the fault-tolerance requirement above and
ask me anything you need clarified.

═══════════════════════════════════════════════════════════════
PROMPT 1 — Project scaffold
═══════════════════════════════════════════════════════════════

Create the project structure below. Don't add files I haven't listed —
I want to review the skeleton before we fill it in.

payroll-fastapi/
├── app/
│   ├── main.py                 # FastAPI app instance, router registration
│   ├── config.py                # pydantic Settings, reads .env
│   ├── database.py              # async SQLAlchemy engine + session
│   ├── models/                  # SQLAlchemy ORM models, one file per table
│   │   ├── user.py
│   │   ├── employee.py
│   │   ├── payroll.py           # PayrollRun + PayrollTransaction
│   │   ├── salary_component.py
│   │   ├── audit_log.py
│   │   └── notification.py
│   ├── schemas/                 # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── employee.py
│   │   ├── payroll.py
│   │   └── notification.py
│   ├── routers/                 # APIRouter per domain
│   │   ├── auth.py
│   │   ├── employees.py
│   │   ├── payroll.py
│   │   ├── reports.py
│   │   └── notifications.py
│   ├── services/                 # business logic, no FastAPI imports here
│   │   ├── payroll_service.py
│   │   ├── notification_service.py
│   │   └── audit_service.py
│   ├── dependencies/             # Depends() functions
│   │   ├── auth.py               # get_current_user, require_role
│   │   └── db.py                  # get_db session dependency
│   └── utils/
│       ├── security.py            # hash_password, verify_password, create_jwt
│       └── logger.py
├── alembic/                       # migrations folder, init with `alembic init`
├── tests/
│   └── test_payroll_service.py
├── .env.example
├── requirements.txt
└── README.md

Generate empty files with a one-line docstring describing each file's
job — no implementation yet. Then run `tree` or list the structure so I
can confirm it matches before we proceed.

═══════════════════════════════════════════════════════════════
PROMPT 2 — Database models
═══════════════════════════════════════════════════════════════

Now implement the SQLAlchemy models in app/models/. Use this exact
schema (I've already designed it — don't deviate):

User: id (UUID pk), email (unique), password_hash, role (enum:
ADMIN/EMPLOYEE), created_at, updated_at

Employee: id (UUID pk), user_id (FK to User, unique — one employee
profile per user), name, department, designation, base_salary
(Numeric(12,2) — NEVER use Float for money), bank_account, ifsc_code,
status (enum: ACTIVE/INACTIVE/ON_LEAVE), joined_at, updated_at

PayrollRun: id (UUID pk), initiated_by (FK to User), month (int 1-12),
year (int), status (enum: PENDING/PROCESSING/COMPLETED/FAILED/PARTIAL),
total_amount (Numeric(14,2)), employee_count (int), initiated_at,
completed_at (nullable). Add a UNIQUE CONSTRAINT on (month, year) — this
prevents double-paying the same month.

PayrollTransaction: id (UUID pk), payroll_run_id (FK), employee_id (FK),
gross_salary (Numeric(12,2)), deductions (Numeric(12,2)), net_salary
(Numeric(12,2)), status (enum: PENDING/SUCCESS/FAILED), failure_reason
(nullable string), processed_at (nullable)

SalaryComponent: id (UUID pk), employee_id (FK), name, type (enum:
ALLOWANCE/DEDUCTION), amount (Numeric(10,2)), is_percentage (bool,
default False), effective_from (date), effective_to (nullable date)

AuditLog: id (UUID pk), performed_by (FK to User), action (string),
entity (string), entity_id (string), changes (JSONB, nullable),
created_at

Notification: id (UUID pk), user_id (FK), type (enum:
PAYROLL_INITIATED/PAYROLL_CREDITED/PAYROLL_FAILED/SALARY_REVISED),
title, message, is_read (bool default False), sent_at

Set up all relationships with back_populates (not backref — I want
explicit two-way navigation). Use UUID primary keys with
default=uuid.uuid4. After writing the models, initialize Alembic and
generate the first migration. Show me the migration file before
applying it.

═══════════════════════════════════════════════════════════════
PROMPT 3 — Auth: register, login, JWT, role-based dependencies
═══════════════════════════════════════════════════════════════

Implement authentication:

1. app/utils/security.py — password hashing with passlib bcrypt,
   create_access_token() using python-jose with a configurable
   expiry from settings, decode_access_token() that raises on
   expired/invalid tokens.

2. app/dependencies/auth.py — a get_current_user dependency that
   extracts the Bearer token, decodes it, fetches the user from DB
   (confirm they still exist), and returns the user object. Also add
   a require_role(*roles) dependency FACTORY (a function that returns
   a dependency) so I can write
   Depends(require_role("ADMIN")) on routes.

3. app/routers/auth.py with three endpoints:
   POST /api/auth/register — public, creates a user
   POST /api/auth/login — public, returns {access_token, token_type, user}
   GET /api/auth/me — protected, returns current user + employee profile
     if it exists

Use the SAME generic error message for "user not found" and "wrong
password" on login — don't leak which emails are registered.

Write this with full docstrings explaining the JWT flow, since I need
to be able to explain this in an interview. After writing, show me how
to test /register and /login with curl so I can verify manually before
moving on.

═══════════════════════════════════════════════════════════════
PROMPT 4 — Employee CRUD + salary components
═══════════════════════════════════════════════════════════════

Implement app/routers/employees.py:

GET    /api/employees           — ADMIN only, paginated, filterable by
                                   department/status/search
GET    /api/employees/{id}      — ADMIN or the employee viewing themselves
POST   /api/employees           — ADMIN only, creates employee profile
                                   linked to an existing user_id
PATCH  /api/employees/{id}      — ADMIN only, partial update
POST   /api/employees/{id}/salary-components — ADMIN only, adds an
                                   allowance or deduction

Use Pydantic schemas in app/schemas/employee.py for request bodies and
responses — validate base_salary > 0, ifsc_code matches the pattern
^[A-Z]{4}0[A-Z0-9]{6}$, bank_account is alphanumeric 9-18 chars.

For the self-view permission check on GET /api/employees/{id}: an
EMPLOYEE role user can only fetch their own employee record, never
anyone else's. Explain in a comment how you're enforcing that.

═══════════════════════════════════════════════════════════════
PROMPT 5 — THE CORE: Payroll service with fault-tolerant processing
═══════════════════════════════════════════════════════════════

This is the most important part of the whole system — take your time.

Implement app/services/payroll_service.py with:

1. calculate_net_salary(employee, salary_components) -> dict
   Pure function, no DB calls. gross = base_salary + sum(allowances),
   deductions = sum(deduction amounts, converting percentage ones to
   base_salary * pct/100), net = max(0, gross - deductions). Round to
   2 decimals. Write this as a pure function so it's independently
   unit-testable.

2. trigger_payroll_run(db, month, year, admin_user_id) -> PayrollRun
   - Check no existing run for that (month, year) unless it's FAILED
   - Fetch all ACTIVE employees with their current salary components
     (effective_from <= today, effective_to is null or >= today)
   - Create a PayrollRun row with status=PROCESSING
   - Kick off process_transactions as a FastAPI BackgroundTask (don't
     await it inline — the HTTP response should return immediately
     with the run id so the admin isn't stuck waiting)
   - Return the run with status PROCESSING

3. process_transactions(run_id, employees) — the background worker
   - Loop through employees ONE AT A TIME
   - For each: open a NEW db session/transaction scoped to just that
     employee (use `async with AsyncSession(engine) as session:` per
     iteration — do not reuse one transaction across all employees)
   - Inside that transaction: create the PayrollTransaction row with
     status=SUCCESS, and create a notification (call
     notification_service). Commit.
   - If any exception is raised for that employee, catch it, roll back
     ONLY that employee's transaction, then in a fresh session write a
     PayrollTransaction row with status=FAILED and the error message in
     failure_reason. Continue the loop — do not let one failure stop
     the rest.
   - After the loop: update PayrollRun.status to COMPLETED (zero
     failures), FAILED (zero successes), or PARTIAL (mixed), and set
     completed_at.

4. retry_failed_transactions(db, run_id) — re-runs process_transactions
   scoped to only the employees whose transactions are currently
   FAILED for that run. Delete the old FAILED rows first, then
   reprocess. Must not touch employees who already succeeded.

Add a code comment block at the top of this file explaining WHY we use
one transaction per employee instead of one transaction for the whole
run — I need to be able to explain this tradeoff in my FTC interview.

Then write app/routers/payroll.py:
POST /api/payroll/trigger              — ADMIN, body {month, year}
GET  /api/payroll/runs                 — ADMIN, paginated list
GET  /api/payroll/runs/{id}            — ADMIN, full status + transactions
POST /api/payroll/runs/{id}/retry      — ADMIN
GET  /api/payroll/my-transactions      — EMPLOYEE, their own salary history

═══════════════════════════════════════════════════════════════
PROMPT 6 — Feature 1: Audit logging
═══════════════════════════════════════════════════════════════

Implement app/services/audit_service.py with a log_action(db,
performed_by, action, entity, entity_id, changes) function.

Then implement it as a reusable dependency or decorator (your choice —
explain which you picked and why) that I can attach to any
state-changing route to automatically log who did what. Wire it into
the employee update route and the payroll trigger route as examples.

Add GET /api/reports/audit-log (ADMIN only, paginated, filterable by
action/entity) in app/routers/reports.py.

═══════════════════════════════════════════════════════════════
PROMPT 7 — Feature 2: Payslip + analytics
═══════════════════════════════════════════════════════════════

Add to app/routers/reports.py:

GET /api/reports/payslip/{transaction_id}
  - ADMIN can view any payslip, EMPLOYEE only their own
  - Returns structured payslip: employee info (mask bank account to
    last 4 digits), itemized earnings (base + each allowance),
    itemized deductions, gross/net summary, payslip number formatted
    as PAY-{year}-{month:02d}-{first 8 chars of transaction id}

GET /api/reports/analytics (ADMIN only)
  - Monthly payout totals for a given year
  - Headcount + average salary + total cost grouped by department
  - Overall stats: active employee count, total payouts this year,
    count of failed transactions

═══════════════════════════════════════════════════════════════
PROMPT 8 — Feature 3: Notifications
═══════════════════════════════════════════════════════════════

Implement app/services/notification_service.py:
- create_notification(db, user_id, type, title, message)
- get_user_notifications(db, user_id, page, limit) -> with unread_count
- mark_as_read(db, user_id, notification_ids: list)
- broadcast_to_all_employees(db, admin_id, title, message)

Wire create_notification into process_transactions from prompt 5 — every
successful payroll transaction should generate a PAYROLL_CREDITED
notification.

Add app/routers/notifications.py:
GET   /api/notifications          — own notifications, paginated
PATCH /api/notifications/read     — mark a list of ids as read
POST  /api/notifications/broadcast — ADMIN only

═══════════════════════════════════════════════════════════════
PROMPT 9 — Tests for the critical path
═══════════════════════════════════════════════════════════════

Write tests/test_payroll_service.py using pytest, testing
calculate_net_salary in isolation (no DB, no async):
- base salary only, no components
- fixed allowance adds correctly
- percentage deduction calculates against base_salary correctly
- mixed allowances + deductions
- net salary floors at 0, never goes negative

Also write one integration test (using a test DB or sqlite in-memory)
that triggers a payroll run with 3 mock employees, forces one to throw
an exception mid-processing, and asserts: the other 2 are SUCCESS, the
forced one is FAILED with a reason recorded, and the run status is
PARTIAL — not FAILED, not COMPLETED.

Run the tests and show me the output.

═══════════════════════════════════════════════════════════════
PROMPT 10 — Seed data + manual verification
═══════════════════════════════════════════════════════════════

Write a seed script (app/seed.py or a script under scripts/) that
creates: 1 admin user, 5 employee users each with an employee profile,
realistic salaries (50k-95k range), and 2 salary components each (an
HRA allowance at 40% of base, a PF deduction at 12% of base).

Run it. Then start the server with uvicorn and show me curl commands to:
1. Login as admin
2. Trigger payroll for the current month
3. Poll the run status until it's COMPLETED
4. Fetch one employee's payslip

Confirm the numbers in the payslip match what calculate_net_salary
would produce by hand for that employee's salary + components.
