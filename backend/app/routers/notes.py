from typing import Annotated, Literal
from datetime import datetime
from pydantic import AwareDatetime

from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.common import Page, VersionBody
from app.schemas.notes import NoteConflict, NoteCreate, NoteRead, NoteUpdate
from app.api import notes as service
from app.events import publish

router = APIRouter(prefix="/notes", tags=["notes"])

CONFLICT = {409: {"model": NoteConflict, "description": "Версия заметки изменилась"}}


@router.get("", response_model=Page[NoteRead])
async def list_notes(
    user: CurrentUser,
    session: Session,
    q: str | None = Query(None, max_length=200),
    tag_ids: Annotated[list[int] | None, Query()] = None,
    is_active: bool | None = None,
    date_from: AwareDatetime | None = None,
    date_to: AwareDatetime | None = None,
    sort: Literal["starts_at", "updated_at"] = "starts_at",
    order: Literal["asc", "desc"] = "asc",
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    return await service.list_notes(
        session, user.id, q=q, tag_ids=tag_ids, is_active=is_active,
        date_from=date_from, date_to=date_to, sort=sort, order=order,
        cursor=cursor, limit=limit,
    )

@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, user: CurrentUser, session: Session):
    note = await service.create_note(session, user, body)
    await publish(user.id, "note.created", note_id=note.id)
    return note


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(note_id: int, user: CurrentUser, session: Session):
    return await service.get_note(session, user.id, note_id)


@router.patch("/{note_id}", response_model=NoteRead, responses=CONFLICT)
async def update_note(note_id: int, body: NoteUpdate, user: CurrentUser, session: Session):
    note = await service.update_note(session, user, note_id, body)
    await publish(user.id, "note.updated", note_id=note.id)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int, user: CurrentUser, session: Session):
    await service.delete_note(session, user, note_id)
    await publish(user.id, "note.deleted", note_id=note_id)

@router.post("/{note_id}/activate", response_model=NoteRead, responses=CONFLICT)
async def activate_note(note_id: int, body: VersionBody, user: CurrentUser, session: Session):
    note = await service.set_active(session, user, note_id, body.version, True)
    await publish(user.id, "note.updated", note_id=note.id)
    return note


@router.post("/{note_id}/deactivate", response_model=NoteRead, responses=CONFLICT)
async def deactivate_note(note_id: int, body: VersionBody, user: CurrentUser, session: Session):
    note = await service.set_active(session, user, note_id, body.version, False)
    await publish(user.id, "note.updated", note_id=note.id)
    return note


@router.post("/{note_id}/restore", response_model=NoteRead)
async def restore_note(note_id: int, user: CurrentUser, session: Session):
    note = await service.restore_note(session, user, note_id)
    await publish(user.id, "note.restored", note_id=note.id)
    return note