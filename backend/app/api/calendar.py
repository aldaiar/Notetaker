from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, exists, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Note, NoteException, Reminder, User
from app.recurrence import expand
from app.schemas.calendar import OccurrenceRead, UpcomingRead
from app.schemas.tags import TagRead
from app.api.notes import _decode_cursor, _encode_cursor

UTC = timezone.utc
MAX_RANGE = timedelta(days=100)


def make_item(note: Note, orig: datetime, ex: NoteException | None) -> OccurrenceRead:
    return OccurrenceRead(
        note_id=note.id,
        occurrence_start=orig,
        starts_at=ex.starts_at if ex and ex.starts_at else orig,
        title=ex.title if ex and ex.title is not None else note.title,
        body=ex.body if ex and ex.body is not None else note.body,
        is_active=note.is_active,
        is_recurring=note.recurrence_freq is not None,
        is_exception=ex is not None,
        tags=[TagRead.model_validate(t) for t in note.tags],
        version=note.version,
    )


def _note_items(
    note: Note, exs: dict[datetime, NoteException], date_from: datetime, date_to: datetime
) -> list[OccurrenceRead]:
    if note.recurrence_freq is None:
        return [make_item(note, note.starts_at, None)]  # диапазон уже отфильтрован в SQL

    originals = dict.fromkeys(
        expand(note.starts_at, note.timezone, note.recurrence_freq.value,
               note.recurrence_until, date_from, date_to)
    )
    # вхождения, перенесённые в диапазон из-за его границ
    for orig, ex in exs.items():
        if orig not in originals and ex.starts_at and date_from <= ex.starts_at < date_to:
            originals[orig] = None

    items = []
    for orig in originals:
        ex = exs.get(orig)
        if ex and ex.is_deleted:
            continue
        actual = ex.starts_at if ex and ex.starts_at else orig
        if date_from <= actual < date_to:  # перенесённое за границу диапазона не показываем
            items.append(make_item(note, orig, ex))
    return items


async def occurrences_between(
    session: AsyncSession,
    user_id: int,
    date_from: datetime,
    date_to: datetime,
    *,
    only_active: bool = False,
    with_reminders: bool = False,
) -> list[OccurrenceRead]:
    date_from, date_to = date_from.astimezone(UTC), date_to.astimezone(UTC)

    moved_in = exists().where(
        NoteException.note_id == Note.id,
        NoteException.is_deleted.is_(False),
        NoteException.starts_at >= date_from,
        NoteException.starts_at < date_to,
    )
    stmt = (
        select(Note)
        .options(selectinload(Note.tags))
        .where(
            Note.user_id == user_id if user_id is not None else true(),
            Note.deleted_at.is_(None),
            or_(
                and_(Note.recurrence_freq.is_(None),
                     Note.starts_at >= date_from, Note.starts_at < date_to),
                and_(Note.recurrence_freq.is_not(None),
                     Note.starts_at < date_to,
                     # -1 день: until хранится в поясе серии, а date_from в UTC
                     or_(Note.recurrence_until.is_(None),
                         Note.recurrence_until >= date_from.date() - timedelta(days=1))),
                moved_in,
            ),
        )
    )

    if with_reminders:
        stmt = stmt.where(exists().where(Reminder.note_id == Note.id))
        
    if only_active:
        stmt = stmt.where(Note.is_active.is_(True))
    notes = list(await session.scalars(stmt))

    by_note: dict[int, dict[datetime, NoteException]] = defaultdict(dict)
    series_ids = [n.id for n in notes if n.recurrence_freq is not None]
    if series_ids:
        rows = await session.scalars(
            select(NoteException).where(
                NoteException.note_id.in_(series_ids),
                or_(
                    and_(NoteException.original_starts_at >= date_from,
                         NoteException.original_starts_at < date_to),
                    and_(NoteException.starts_at >= date_from,
                         NoteException.starts_at < date_to),
                ),
            )
        )
        for ex in rows:
            by_note[ex.note_id][ex.original_starts_at] = ex

    items = [i for n in notes for i in _note_items(n, by_note[n.id], date_from, date_to)]
    items.sort(key=lambda o: (o.starts_at, o.note_id))
    return items


def _local_midnight(d, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.min, tzinfo=tz).astimezone(UTC)


async def get_upcoming(
    session: AsyncSession,
    user: User,
    past_cursor: str | None,
    past_limit: int,
    past_days: int,
) -> UpcomingRead:
    now = datetime.now(UTC)
    tz = ZoneInfo(user.timezone)
    today = now.astimezone(tz).date()
    end_today = _local_midnight(today + timedelta(days=1), tz)
    end_week = _local_midnight(today + timedelta(days=7), tz)  # сегодня + ещё 6 дней

    ahead = await occurrences_between(session, user.id, now, end_week, only_active=True)
    past = await occurrences_between(
        session, user.id, now - timedelta(days=past_days), now, only_active=True
    )

    past.sort(key=lambda o: (o.starts_at, o.note_id), reverse=True)
    if past_cursor:
        ts, nid = _decode_cursor(past_cursor)
        past = [o for o in past if (o.starts_at, o.note_id) < (ts, nid)]
    page = past[:past_limit]
    next_cursor = (
        _encode_cursor(page[-1].starts_at, page[-1].note_id) if len(past) > past_limit else None
    )

    return UpcomingRead(
        server_time=now,
        today=[o for o in ahead if o.starts_at < end_today],
        week=[o for o in ahead if o.starts_at >= end_today],
        past=page,
        past_next_cursor=next_cursor,
    )