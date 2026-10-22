import asyncio
import logging

from app.db.database import SessionLocal  # подставьте своё имя фабрики сессий
from app.api.reminders import process_due

log = logging.getLogger(__name__)
TICK_SECONDS = 15


async def scheduler_loop() -> None:
    while True:
        try:
            await process_due(SessionLocal)
        except Exception:
            log.exception("Ошибка тика планировщика")
        await asyncio.sleep(TICK_SECONDS)
