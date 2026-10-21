import base64
import json

from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Literal

from fastapi import HTTPException, status

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy import and_, exists, or_, tuple_

from app.exceptions import VersionConflict
from app.db.models import Note, NoteException, Reminder, Tag, User, note_tags 
from app.schemas.notes import NoteCreate, NoteUpdate


_LOAD = (selectinload(Note.tags), selectinload(Note.reminders))


# ---------- вспомогательное ----------

async def _fetch(
    session: AsyncSession, user_id: int, note_id: int, *, in_trash: bool = False
) -> Note:
    """Заметка пользователя вместе с тегами и напоминаниями. Всегда свежая из БД."""
    trash_filter = Note.deleted_at.is_not(None) if in_trash else Note.deleted_at.is_(None)
    note = await session.scalar(
        select(Note)
        .options(*_LOAD)
        .where(Note.id == note_id, Note.user_id == user_id, trash_filter)
        .execution_options(populate_existing=True)
    )
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заметка не найдена")
    return note


async def get_note(session: AsyncSession, user_id: int, note_id: int) -> Note:
    return await _fetch(session, user_id, note_id)


def _check_version(note: Note, version: int) -> None:
    if note.version != version:
        raise VersionConflict(note)


async def _load_tags(session: AsyncSession, user_id: int, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = list(
        await session.scalars(
            select(Tag).where(Tag.user_id == user_id, Tag.id.in_(tag_ids))
        )
    )
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Некоторые теги не найдены")
    return tags


def _check_until(starts_at: datetime, until: date | None, tz: str) -> None:
    if until is not None and until < starts_at.astimezone(ZoneInfo(tz)).date():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Дата окончания повторов раньше даты заметки",
        )


async def _commit(session: AsyncSession, user_id: int, note_id: int) -> Note:
    """Коммит + защита от гонки: StaleDataError превращается в 409 с актуальной заметкой."""
    try:
        await session.commit()
    except StaleDataError:
        await session.rollback()
        raise VersionConflict(await _fetch(session, user_id, note_id))
    return await _fetch(session, user_id, note_id)


# ---------- операции ----------

async def create_note(session: AsyncSession, user: User, data: NoteCreate) -> Note:
    if data.recurrence:
        _check_until(data.starts_at, data.recurrence.until, user.timezone)

    note = Note(
        user_id=user.id,
        title=data.title,
        body=data.body,
        starts_at=data.starts_at,
        is_active=data.is_active,
        recurrence_freq=data.recurrence.freq if data.recurrence else None,
        recurrence_until=data.recurrence.until if data.recurrence else None,
        tags=await _load_tags(session, user.id, data.tag_ids),
        reminders=[Reminder(offset_minutes=m) for m in data.reminders],
    )
    session.add(note)
    await session.flush()
    note_id = note.id  # забираем до commit, после него атрибуты могут быть expired
    # TODO(scheduler): создать расписание напоминаний для note
    return await _commit(session, user.id, note_id)


async def update_note(
    session: AsyncSession, user: User, note_id: int, data: NoteUpdate
) -> Note:
    note = await _fetch(session, user.id, note_id)
    _check_version(note, data.version)
    

    fields = data.model_fields_set
    series_changed = False

    if "title" in fields:
        note.title = data.title
    if "body" in fields:
        note.body = data.body

    if "starts_at" in fields and data.starts_at != note.starts_at:
        note.starts_at = data.starts_at
        series_changed = True

    if "recurrence" in fields:
        new_freq = data.recurrence.freq if data.recurrence else None
        new_until = data.recurrence.until if data.recurrence else None
        if new_freq != note.recurrence_freq:
            series_changed = True
        note.recurrence_freq = new_freq
        note.recurrence_until = new_until

    _check_until(note.starts_at, note.recurrence_until, user.timezone)

    if "tag_ids" in fields:
        note.tags = await _load_tags(session, user.id, data.tag_ids)

    if "reminders" in fields:
        wanted = set(data.reminders)
        current = {r.offset_minutes: r for r in note.reminders}
        for offset, reminder in current.items():
            if offset not in wanted:
                note.reminders.remove(reminder)  # delete-orphan удалит строку
        for offset in wanted - current.keys():
            note.reminders.append(Reminder(offset_minutes=offset))

    
    if series_changed:
        # Сдвинули начало или частоту серии: старые исключения привязаны к
        # прежней сетке вхождений и теряют смысл, поэтому сбрасываем их.
        with session.no_autoflush:
            await session.execute(
                delete(NoteException).where(
                    NoteException.note_id == note.id
                )
            )
    # Явно трогаем строку: иначе при правке только тегов/напоминаний UPDATE notes
    # не выполнится, и version с updated_at не изменятся.
    note.updated_at = func.now()

    # TODO(scheduler): пересчитать расписание, если менялись starts_at/reminders/recurrence
    return await _commit(session, user.id, note.id)


async def set_active(
    session: AsyncSession, user: User, note_id: int, version: int, active: bool
) -> Note:
    note = await _fetch(session, user.id, note_id)
    _check_version(note, version)
    note.is_active = active
    note.updated_at = func.now()
    return await _commit(session, user.id, note.id)


async def delete_note(session: AsyncSession, user: User, note_id: int) -> None:
    note = await _fetch(session, user.id, note_id)
    note.deleted_at = func.now()
    try:
        await session.commit()
    except StaleDataError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Заметка изменилась, повторите удаление"
        )


async def restore_note(session: AsyncSession, user: User, note_id: int) -> Note:
    note = await _fetch(session, user.id, note_id, in_trash=True)
    note.deleted_at = None
    note.updated_at = func.now() 
    return await _commit(session, user.id, note.id)
    # Напоминания с ещё не наступившим сроком вернутся сами по той же причине.




def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _encode_cursor(value: datetime, note_id: int) -> str:
    raw = json.dumps({"v": value.isoformat(), "id": note_id})
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        value = datetime.fromisoformat(data["v"])
        note_id = int(data["id"])

        if value.tzinfo is None or value.utcoffset() is None or note_id < 1:
            raise ValueError

        return value, note_id
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный cursor",
        )


async def list_notes(
    session: AsyncSession,
    user_id: int,
    *,
    q: str | None,
    tag_ids: list[int] | None,
    is_active: bool | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort: Literal["starts_at", "updated_at"],
    order: Literal["asc", "desc"],
    cursor: str | None,
    limit: int,
) -> dict:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from не может быть позже date_to",
        )

    q = q.strip() if q else None
    sort_col = Note.starts_at if sort == "starts_at" else Note.updated_at
    stmt = (
        select(Note)
        .options(*_LOAD)
        .where(Note.user_id == user_id, Note.deleted_at.is_(None))
    )

    if q:
        pattern = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(Note.title.ilike(pattern, escape="\\"), Note.body.ilike(pattern, escape="\\"))
        )

    if tag_ids:  # заметки, у которых есть хотя бы один из тегов
        stmt = stmt.where(
            exists().where(note_tags.c.note_id == Note.id, note_tags.c.tag_id.in_(tag_ids))
        )

    if is_active is not None:
        stmt = stmt.where(Note.is_active == is_active)

    if date_from or date_to:
        single = [Note.recurrence_freq.is_(None)]
        series = [Note.recurrence_freq.is_not(None)]
        if date_from:
            single.append(Note.starts_at >= date_from)
            series.append(or_(Note.recurrence_until.is_(None),
                              Note.recurrence_until >= date_from.date()))
        if date_to:
            single.append(Note.starts_at <= date_to)
            series.append(Note.starts_at <= date_to)
        stmt = stmt.where(or_(and_(*single), and_(*series)))

    if cursor:
        value, last_id = _decode_cursor(cursor)
        pair, bound = tuple_(sort_col, Note.id), tuple_(value, last_id)
        stmt = stmt.where(pair > bound if order == "asc" else pair < bound)

    direction = (lambda c: c.asc()) if order == "asc" else (lambda c: c.desc())
    stmt = stmt.order_by(direction(sort_col), direction(Note.id)).limit(limit + 1)

    rows = list(await session.scalars(stmt))
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = (
        _encode_cursor(getattr(items[-1], sort), items[-1].id) if has_more else None
    )
    return {"items": items, "next_cursor": next_cursor}