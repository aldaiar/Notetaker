from datetime import datetime

from fastapi import APIRouter, Query

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.calendar import OccurrenceRead, UpcomingRead

router = APIRouter(tags=["calendar"])


@router.get("/calendar", response_model=list[OccurrenceRead])
async def get_calendar(
    user: CurrentUser,
    session: Session,
    date_from: datetime = Query(..., alias="from"),
    date_to: datetime = Query(..., alias="to"),
):
    """Вхождения в диапазоне: месяц, неделя и день отличаются только диапазоном."""
    not_implemented()


@router.get("/upcoming", response_model=UpcomingRead)
async def get_upcoming(
    user: CurrentUser,
    session: Session,
    past_cursor: str | None = None,
    past_limit: int = Query(50, ge=1, le=200),
):
    not_implemented()