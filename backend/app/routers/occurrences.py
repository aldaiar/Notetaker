from fastapi import APIRouter, Query, status
from pydantic import AwareDatetime

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.calendar import OccurrenceRead
from app.schemas.notes import NoteConflict, OccurrenceScope, OccurrenceUpdate

router = APIRouter(prefix="/notes/{note_id}/occurrences", tags=["occurrences"])


@router.patch(
    "/{occurrence_start}",
    response_model=OccurrenceRead,
    responses={409: {"model": NoteConflict}},
)
async def update_occurrence(
    note_id: int,
    occurrence_start: AwareDatetime,  # ISO в UTC с Z, например 2026-11-03T09:00:00Z
    body: OccurrenceUpdate,
    user: CurrentUser,
    session: Session,
):
    """
    scope=this: запись в note_exceptions.
    scope=following: серия делится, у старой until = день до вхождения, создаётся новая серия.
    """
    not_implemented()


@router.delete("/{occurrence_start}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_occurrence(
    note_id: int,
    occurrence_start: AwareDatetime,
    user: CurrentUser,
    session: Session,
    scope: OccurrenceScope = Query(...),
    version: int = Query(..., ge=1),
):
    not_implemented()