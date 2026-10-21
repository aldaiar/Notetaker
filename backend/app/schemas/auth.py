from pydantic import EmailStr

from app.schemas.common import BaseModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"