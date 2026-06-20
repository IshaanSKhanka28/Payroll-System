from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.employees import router as employees_router
from app.routers.payroll import router as payroll_router
from app.routers.reports import router as reports_router
from app.routers.notifications import router as notifications_router

app = FastAPI(title="Payroll System API")

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(payroll_router)
app.include_router(reports_router)
app.include_router(notifications_router)




@app.get("/")
async def root():
    return {"message": "Payroll System API is running"}
