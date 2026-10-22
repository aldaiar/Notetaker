from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Note, NoteException, Reminder, User
from app.recurrence import is_occurrence, local_date
from app.schemas.calendar import OccurrenceRead
from app.schemas.notes import OccurrenceScope, OccurrenceUpdate
from app.api import notes as ns
from app.api.calendar import make_item

UTC = timezone.utc


async def _exception(session: AsyncSession, note_id: int, orig: datetime) -> NoteException | None:
    return await session.scalar(
        select(NoteException).where(
            NoteException.note_id == note_id, NoteException.original_starts_at == orig
        )
    )


async def _load_series(
    session: AsyncSession, user: User, note_id: int, orig: datetime, version: int
) -> Note:
    note = await ns._fetch(session, user.id, note_id)
    ns._check_version(note, version)
    if note.recurrence_freq is None:
        raise HTTPException(400, "Заметка не повторяется, используйте PATCH /notes/{id}")
    if not is_occurrence(
        note.starts_at, note.timezone, note.recurrence_freq.value, note.recurrence_until, orig
    ):
        raise HTTPException(404, "Вхождение не найдено")
    # Любое изменение вхождения меняет серию: поднимаем version и updated_at,
    # чтобы другие вкладки увидели правку. Ставим до любых запросов, иначе
    # autoflush отправит два UPDATE и version вырастет на 2.
    note.updated_at = func.now()
    return note


def _day_before(orig: datetime, tz_name: str):
    return local_date(orig, tz_name) - timedelta(days=1)


async def update_occurrence(
    session: AsyncSession, user: User, note_id: int, orig: datetime, data: OccurrenceUpdate
) -> OccurrenceRead:
    orig = orig.astimezone(UTC)
    note = await _load_series(session, user, note_id, orig, data.version)
    fields = data.model_fields_set & {"title", "body", "starts_at"}

    # ---------- только это вхождение ----------
    if data.scope is OccurrenceScope.this:
        ex = await _exception(session, note.id, orig)
        if ex is not None and ex.is_deleted:
            raise HTTPException(404, "Вхождение удалено")
        if ex is None:
            ex = NoteException(note_id=note.id, original_starts_at=orig, is_deleted=False)
            session.add(ex)
        for f in fields:  # явный null = «как в серии»
            setattr(ex, f, getattr(data, f))
        note = await ns._commit(session, user.id, note.id)
        return make_item(note, orig, await _exception(session, note.id, orig))

    # ---------- это и все следующие ----------
    values = {f: getattr(data, f) for f in fields if getattr(data, f) is not None}
    new_start = values.get("starts_at", orig)
    old_id = note.id

    if orig == note.starts_at:  # с первого вхождения = вся серия
        grid_changed = new_start != note.starts_at
        for f, v in values.items():
            setattr(note, f, v)
        ns._check_until(note.starts_at, note.recurrence_until, note.timezone)
        if grid_changed:  # сетка сдвинулась: исключения теряют смысл
            await session.execute(delete(NoteException).where(NoteException.note_id == old_id))
        else:  # правка «этого» вхождения не должна перебивать новые значения
            await session.execute(
                delete(NoteException).where(
                    NoteException.note_id == old_id, NoteException.original_starts_at == orig
                )
            )
        note = await ns._commit(session, user.id, old_id)
        return make_item(note, note.starts_at, None)

    # серия делится: старая заканчивается накануне, дальше новая
    ns._check_until(new_start, note.recurrence_until, note.timezone)
    new_note = Note(
        user_id=user.id,
        title=values.get("title", note.title),
        body=values.get("body", note.body),
        starts_at=new_start,
        is_active=note.is_active,
        timezone=note.timezone,
        recurrence_freq=note.recurrence_freq,
        recurrence_until=note.recurrence_until,
        tags=list(note.tags),
        reminders=[Reminder(offset_minutes=r.offset_minutes) for r in note.reminders],
    )
    note.recurrence_until = _day_before(orig, note.timezone)  # до любых запросов
    session.add(new_note)
    await session.flush()
    new_id = new_note.id

    # исключения: «это» вхождение сбрасываем, будущие переносим, если сетка та же
    await session.execute(
        delete(NoteException).where(
            NoteException.note_id == old_id,
            NoteException.original_starts_at >= orig
            if new_start != orig
            else NoteException.original_starts_at == orig,
        )
    )
    if new_start == orig:
        await session.execute(
            update(NoteException)
            .where(NoteException.note_id == old_id, NoteException.original_starts_at > orig)
            .values(note_id=new_id)
        )
    # TODO(scheduler): пересоздать расписание напоминаний для обеих серий

    new_note = await ns._commit(session, user.id, new_id, conflict_id=old_id)
    return make_item(new_note, new_start, None)


async def delete_occurrence(
    session: AsyncSession,
    user: User,
    note_id: int,
    orig: datetime,
    scope: OccurrenceScope,
    version: int,
) -> None:
    orig = orig.astimezone(UTC)
    note = await _load_series(session, user, note_id, orig, version)

    if scope is OccurrenceScope.this:
        ex = await _exception(session, note.id, orig)
        if ex is None:
            session.add(NoteException(note_id=note.id, original_starts_at=orig, is_deleted=True))
        else:
            ex.is_deleted = True
            ex.title = ex.body = ex.starts_at = None
    elif orig == note.starts_at:
        note.deleted_at = func.now()  # удаление с первого вхождения = вся серия в корзину
    else:
        note.recurrence_until = _day_before(orig, note.timezone)
        await session.execute(
            delete(NoteException).where(
                NoteException.note_id == note.id, NoteException.original_starts_at >= orig
            )
        )
    await ns._save(session, user.id, note.id)