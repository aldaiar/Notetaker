from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import EmailStr, field_validator, Field

from app.schemas.common import BaseModel, ORMModel



class UserRead(ORMModel):
    id: int
    email: EmailStr
    username: str
    timezone: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=4, max_length=64)
    password: str = Field(min_length=8)
    timezone: str = Field(default="UTC", max_length=64)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Неизвестный часовой пояс, ожидается IANA, например Asia/Bishkek")
        return v