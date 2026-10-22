from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Note, NoteException, Notification, Reminder, note_tags
from app.api.notes import _LOAD, _decode_cursor, _encode_cursor

TRASH_DAYS = 30


async def list_trash(session: AsyncSession, user_id: int, cursor: str | None, limit: int) -> dict:
    stmt = (
        select(Note).options(*_LOAD)
        .where(Note.user_id == user_id, Note.deleted_at.is_not(None))
    )
    if cursor:
        value, last_id = _decode_cursor(cursor)
        stmt = stmt.where(tuple_(Note.deleted_at, Note.id) < tuple_(value, last_id))
    rows = list(await session.scalars(
        stmt.order_by(Note.deleted_at.desc(), Note.id.desc()).limit(limit + 1)
    ))
    items = rows[:limit]
    next_cursor = _encode_cursor(items[-1].deleted_at, items[-1].id) if len(rows) > limit else None
    return {"items": items, "next_cursor": next_cursor}


async def hard_delete(session: AsyncSession, ids: list[int]) -> None:
    """Явное удаление зависимых строк: не зависим от того, как настроены FK.
    reminder_deliveries уходят каскадом вместе с reminders."""
    await session.execute(delete(NoteException).where(NoteException.note_id.in_(ids)))
    await session.execute(delete(Reminder).where(Reminder.note_id.in_(ids)))
    await session.execute(delete(note_tags).where(note_tags.c.note_id.in_(ids)))
    await session.execute(delete(Notification).where(Notification.note_id.in_(ids)))
    await session.execute(delete(Note).where(Note.id.in_(ids)))


async def purge_note(session: AsyncSession, user_id: int, note_id: int) -> None:
    found = await session.scalar(
        select(Note.id).where(
            Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_not(None)
        )
    )
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заметки нет в корзине")
    await hard_delete(session, [note_id])
    await session.commit()


async def empty_trash(session: AsyncSession, user_id: int) -> None:
    ids = list(await session.scalars(
        select(Note.id).where(Note.user_id == user_id, Note.deleted_at.is_not(None))
    ))
    if ids:
        await hard_delete(session, ids)
        await session.commit()


async def purge_expired(session_factory, days: int = TRASH_DAYS) -> int:
    """Автоочистка: заметки, пролежавшие в корзине дольше `days` дней. Порциями по 500."""
    total = 0
    while True:
        async with session_factory() as session:
            ids = list(await session.scalars(
                select(Note.id)
                .where(Note.deleted_at < func.now() - timedelta(days=days))
                .limit(500)
            ))
            if not ids:
                return total
            await hard_delete(session, ids)
            await session.commit()
            total += len(ids)