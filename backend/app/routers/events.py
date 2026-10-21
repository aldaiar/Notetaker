from fastapi import APIRouter

from app.deps import CurrentUser, not_implemented

router = APIRouter(tags=["realtime"])


@router.get("/events")
async def events(user: CurrentUser):
    """
    SSE-поток (text/event-stream) с событиями пользователя:
    note.created|updated|deleted|restored, tag.*, settings.updated, notification.new.
    """
    not_implemented()