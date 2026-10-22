from fastapi import APIRouter, Query, status
from pydantic import AwareDatetime

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.calendar import OccurrenceRead
from app.schemas.notes import NoteConflict, OccurrenceScope, OccurrenceUpdate
from app.api import occurrences as service


router = APIRouter(prefix="/notes/{note_id}/occurrences", tags=["occurrences"])


@router.patch("/{occurrence_start}", response_model=OccurrenceRead,
              responses={409: {"model": NoteConflict}})
async def update_occurrence(
    note_id: int, occurrence_start: AwareDatetime, body: OccurrenceUpdate,
    user: CurrentUser, session: Session,
):
    return await service.update_occurrence(session, user, note_id, occurrence_start, body)


@router.delete("/{occurrence_start}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_occurrence(
    note_id: int, occurrence_start: AwareDatetime, user: CurrentUser, session: Session,
    scope: OccurrenceScope = Query(...), version: int = Query(..., ge=1),
):
    await service.delete_occurrence(session, user, note_id, occurrence_start, scope, version)
