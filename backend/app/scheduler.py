import asyncio
import logging

from app.db.database import SessionLocal  # подставьте своё имя фабрики сессий
from app.api.reminders import process_due
from app.api.trash import purge_expired


log = logging.getLogger(__name__)
TICK_SECONDS = 15
CLEANUP_SECONDS = 3600

async def scheduler_loop() -> None:
    while True:
        try:
            await process_due(SessionLocal)
        except Exception:
            log.exception("Ошибка тика планировщика")
        await asyncio.sleep(TICK_SECONDS)





async def cleanup_loop() -> None:
    while True:  # первый проход сразу при старте, дальше раз в час
        try:
            removed = await purge_expired(SessionLocal)
            if removed:
                log.info("Корзина: удалено %s заметок старше 30 дней", removed)
        except Exception:
            log.exception("Ошибка автоочистки корзины")
        await asyncio.sleep(CLEANUP_SECONDS)