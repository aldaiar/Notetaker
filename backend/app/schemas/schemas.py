from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=4, max_length=64)
    password: str = Field(min_length=8)
    timezone: str = Field(default="UTC", max_length=64)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    timezone: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"