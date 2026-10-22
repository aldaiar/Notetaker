from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, Session
from app.events import publish
from app.schemas.common import Page
from app.schemas.notes import NoteRead
from app.api import trash as service

router = APIRouter(prefix="/trash", tags=["trash"])


@router.get("", response_model=Page[NoteRead])
async def list_trash(
    user: CurrentUser, session: Session,
    cursor: str | None = None, limit: int = Query(50, ge=1, le=200),
):
    """Новые удалённые первыми. Срок хранения: deleted_at + 30 дней."""
    return await service.list_trash(session, user.id, cursor, limit)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_note(note_id: int, user: CurrentUser, session: Session):
    uid = user.id
    await service.purge_note(session, uid, note_id)
    await publish(uid, "note.purged", note_id=note_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def empty_trash(user: CurrentUser, session: Session):
    uid = user.id
    await service.empty_trash(session, uid)
    await publish(uid, "trash.emptied")
