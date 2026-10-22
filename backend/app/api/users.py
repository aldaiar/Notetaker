from fastapi import Depends, HTTPException, status

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user
from app.db.models import User
from app.schemas.users import UserRead, UserUpdate



async def update_me(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await session.get(User, user_id)
    for field in ("email", "timezone"):
        value = getattr(data, field)
        if field in data.model_fields_set and value is not None:
            setattr(user, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже занят")
    await session.refresh(user)
    return user