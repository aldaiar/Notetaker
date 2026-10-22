import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.mailer import send_email
from app.db.models import Note, Notification, Reminder, ReminderDelivery, User
from app.api.calendar import occurrences_between

log = logging.getLogger(__name__)
UTC = timezone.utc
MAX_OFFSET = 1440
LEAD = {10: "через 10 минут", 60: "через час", 1440: "завтра"}


async def process_due(session_factory) -> int:
    now = datetime.now(UTC)
    sent = 0
    async with session_factory() as session:
        items = await occurrences_between(
            session, None, now, now + timedelta(minutes=MAX_OFFSET + 1),
            only_active=True, with_reminders=True,
        )
        if not items:
            return 0

        note_ids = {i.note_id for i in items}
        # плоские кортежи: после commit ORM-объекты истекают, а в async это MissingGreenlet
        by_note: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for rid, nid, off in await session.execute(
            select(Reminder.id, Reminder.note_id, Reminder.offset_minutes)
            .where(Reminder.note_id.in_(note_ids))
        ):
            by_note[nid].append((rid, off))
        owner = {
            nid: (uid, email, tz)
            for nid, uid, email, tz in await session.execute(
                select(Note.id, User.id, User.email, User.timezone)
                .join(User, User.id == Note.user_id).where(Note.id.in_(note_ids))
            )
        }

        for item in items:
            for rid, offset in by_note[item.note_id]:
                fire_at = item.starts_at - timedelta(minutes=offset)
                if not (fire_at <= now < item.starts_at):
                    continue  # рано, или вхождение уже прошло (пропущенное не досылаем)

                # атомарно «занимаем» отправку: второй воркер получит None
                claim = await session.scalar(
                    pg_insert(ReminderDelivery)
                    .values(reminder_id=rid, occurrence_starts_at=item.occurrence_start)
                    .on_conflict_do_nothing(index_elements=["reminder_id", "occurrence_starts_at"])
                    .returning(ReminderDelivery.id)
                )
                await session.commit()
                if claim is None:
                    continue

                uid, email, tz = owner[item.note_id]
                when = item.starts_at.astimezone(ZoneInfo(tz)).strftime("%d.%m.%Y %H:%M")
                try:
                    await send_email(
                        email,
                        f"Напоминание: {item.title}",
                        f"«{item.title}» {LEAD[offset]}: {when} ({tz}).",
                    )
                except Exception:
                    log.exception("Не удалось отправить письмо, повторим на следующем тике")
                    await session.execute(delete(ReminderDelivery).where(ReminderDelivery.id == claim))
                    await session.commit()
                    continue

                session.add(Notification(
                    user_id=uid, note_id=item.note_id, title=item.title,
                    occurrence_starts_at=item.occurrence_start,
                ))
                await session.commit()
                sent += 1
    return sent