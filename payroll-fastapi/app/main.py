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




from fastapi.responses import HTMLResponse
import os

@app.get("/", response_class=HTMLResponse)
async def root():
    path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

