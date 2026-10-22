from fastapi import APIRouter, Query, status
from pydantic import AwareDatetime

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.calendar import OccurrenceRead
from app.schemas.notes import NoteConflict, OccurrenceScope, OccurrenceUpdate
from app.api import occurrences as service
from app.events import publish

router = APIRouter(prefix="/notes/{note_id}/occurrences", tags=["occurrences"])


@router.patch("/{occurrence_start}", response_model=OccurrenceRead,
              responses={409: {"model": NoteConflict}})
async def update_occurrence(
    note_id: int, occurrence_start: AwareDatetime, body: OccurrenceUpdate,
    user: CurrentUser, session: Session,
):
    item = await service.update_occurrence(session, user, note_id, occurrence_start, body)
    await publish(user.id, "note.updated", note_id=note_id)
    if item.note_id != note_id:  # «это и следующие» создало новую серию
        await publish(user.id, "note.created", note_id=item.note_id)
    return item


@router.delete("/{occurrence_start}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_occurrence(
    note_id: int, occurrence_start: AwareDatetime, user: CurrentUser, session: Session,
    scope: OccurrenceScope = Query(...), version: int = Query(..., ge=1),
):
    await service.delete_occurrence(session, user, note_id, occurrence_start, scope, version)
    await publish(user.id, "note.updated", note_id=note_id)
