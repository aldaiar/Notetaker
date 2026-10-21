from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.db.models import User
from backend.app.schemas.schemas import UserRead
from app.routers.users import router


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user