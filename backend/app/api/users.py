from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.db.models import User
from app.schemas import UserRead


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user