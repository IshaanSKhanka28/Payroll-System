import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class EmployeeMinResponse(BaseModel):
    id: uuid.UUID
    name: str
    department: str
    designation: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(UserResponse):
    employee: EmployeeMinResponse | None = None


class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None
