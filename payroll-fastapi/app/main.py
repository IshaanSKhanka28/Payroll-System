from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.employees import router as employees_router

app = FastAPI(title="Payroll System API")

app.include_router(auth_router)
app.include_router(employees_router)


@app.get("/")
async def root():
    return {"message": "Payroll System API is running"}
