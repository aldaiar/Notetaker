from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest, Token
from app.security import create_access_token, verify_password


router = APIRouter(
    prefix="/auth/login",
    tags=["Authentication"],
)


@router.post("", response_model=Token)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(User).where(User.email == str(data.email))
    )

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)

    return Token(
        access_token=access_token,
        token_type="bearer",
    )