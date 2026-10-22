import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict

import asyncpg
from sqlalchemy import text

from app.config import settings
from app.db.database import engine

log = logging.getLogger(__name__)
CHANNEL = "events"
TOKEN_TTL = 60  # секунд, токен нужен только в момент подключения


# ---------- публикация ----------

async def publish(user_id: int, type_: str, **data) -> None:
    """Вызывать после успешного commit. Ошибка шины не должна ломать запрос."""
    payload = json.dumps({"user_id": user_id, "type": type_, **data}, default=str)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT pg_notify(:c, :p)"), {"c": CHANNEL, "p": payload})
    except Exception:
        log.exception("Не удалось опубликовать событие %s", type_)


# ---------- раздача подписчикам внутри процесса ----------

class Hub:
    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, user_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subs[user_id].add(q)
        return q

    def unsubscribe(self, user_id: int, q: asyncio.Queue) -> None:
        self._subs[user_id].discard(q)
        if not self._subs[user_id]:
            del self._subs[user_id]

    def dispatch(self, payload: str) -> None:
        try:
            event = json.loads(payload)
        except ValueError:
            return
        for q in list(self._subs.get(event.get("user_id"), ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # медленный клиент: после переподключения он всё равно перечитает данные


hub = Hub()


async def listen_loop() -> None:
    """Один LISTEN-коннект на процесс; при обрыве переподключается."""
    dsn = settings.database_url.replace("+asyncpg", "")
    while True:
        conn = None
        try:
            conn = await asyncpg.connect(dsn)
            await conn.add_listener(CHANNEL, lambda _c, _pid, _ch, payload: hub.dispatch(payload))
            log.info("LISTEN %s подключён", CHANNEL)
            while True:
                await asyncio.sleep(20)
                await conn.execute("SELECT 1")  # keepalive и обнаружение обрыва
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("LISTEN-коннект потерян, переподключаюсь")
            await asyncio.sleep(2)
        finally:
            if conn is not None and not conn.is_closed():
                await conn.close()


# ---------- короткоживущий токен для EventSource ----------

def _sign(raw: str) -> str:
    return hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()


def make_token(user_id: int) -> str:
    raw = f"{user_id}:{int(time.time()) + TOKEN_TTL}"
    return base64.urlsafe_b64encode(f"{raw}:{_sign(raw)}".encode()).decode()


def read_token(token: str) -> int | None:
    try:
        uid, exp, sig = base64.urlsafe_b64decode(token.encode()).decode().split(":")
        raw = f"{uid}:{exp}"
        if hmac.compare_digest(sig, _sign(raw)) and int(exp) >= time.time():
            return int(uid)
    except Exception:
        pass
    return None