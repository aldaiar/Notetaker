from fastapi import APIRouter, HTTPException, Query
from pydantic import AwareDatetime

from app.deps import CurrentUser, Session
from app.schemas.calendar import OccurrenceRead, UpcomingRead
from app.api import calendar as service

router = APIRouter(tags=["calendar"])


@router.get("/calendar", response_model=list[OccurrenceRead])
async def get_calendar(
    user: CurrentUser,
    session: Session,
    date_from: AwareDatetime = Query(..., alias="from"),
    date_to: AwareDatetime = Query(..., alias="to"),
):
    """Вхождения в [from, to). Месяц, неделя и день отличаются только диапазоном."""
    if date_to <= date_from:
        raise HTTPException(422, "to должно быть позже from")
    if date_to - date_from > service.MAX_RANGE:
        raise HTTPException(422, "Слишком большой диапазон (максимум 100 дней)")
    return await service.occurrences_between(session, user.id, date_from, date_to)


@router.get("/upcoming", response_model=UpcomingRead)
async def get_upcoming(
    user: CurrentUser,
    session: Session,
    past_cursor: str | None = None,
    past_limit: int = Query(50, ge=1, le=200),
    past_days: int = Query(30, ge=1, le=365),
):
    return await service.get_upcoming(session, user, past_cursor, past_limit, past_days)