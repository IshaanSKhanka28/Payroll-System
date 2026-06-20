from fastapi import FastAPI
from app.routers.auth import router as auth_router

app = FastAPI(title="Payroll System API")

app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": "Payroll System API is running"}
