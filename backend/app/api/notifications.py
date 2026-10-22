from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def list_notifications(session: AsyncSession, user_id: int, unseen: bool):
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unseen:
        stmt = stmt.where(Notification.seen_at.is_(None))
    return list(await session.scalars(stmt.order_by(Notification.id.desc()).limit(100)))


async def mark_seen(session: AsyncSession, user_id: int, notification_id: int) -> None:
    n = await session.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    if n is None:
        raise HTTPException(404, "Уведомление не найдено")
    if n.seen_at is None:
        n.seen_at = func.now()
        await session.commit()