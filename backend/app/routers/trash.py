from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.common import Page
from app.schemas.notes import NoteRead

router = APIRouter(prefix="/trash", tags=["trash"])


@router.get("", response_model=Page[NoteRead])
async def list_trash(
    user: CurrentUser,
    session: Session,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    not_implemented()


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_note(note_id: int, user: CurrentUser, session: Session):
    """Удалить навсегда."""
    not_implemented()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def empty_trash(user: CurrentUser, session: Session):
    not_implemented()