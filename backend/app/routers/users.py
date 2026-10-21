from fastapi import APIRouter

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.users import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(body: UserUpdate, user: CurrentUser, session: Session):
    """Смена email и часового пояса. Расписание напоминаний (UTC) не трогается."""
    not_implemented()