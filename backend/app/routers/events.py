import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.deps import CurrentUser
from app.events import hub, make_token, read_token

router = APIRouter(tags=["realtime"])


@router.post("/events/token")
async def events_token(user: CurrentUser):
    """Токен на 60 секунд: EventSource не умеет заголовки Authorization."""
    return {"token": make_token(user.id)}


@router.get("/events")
async def events(request: Request, token: str = Query(...)):
    user_id = read_token(token)
    if user_id is None:
        raise HTTPException(401, "Недействительный или просроченный токен")

    async def stream():
        q = hub.subscribe(user_id)
        try:
            yield "retry: 3000\n\n"
            yield f"event: hello\ndata: {json.dumps({'type': 'hello'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # держит соединение живым за прокси
        finally:
            hub.unsubscribe(user_id, q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )