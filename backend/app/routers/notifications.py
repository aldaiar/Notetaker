from fastapi import APIRouter, status

from app.deps import CurrentUser, Session, not_implemented
from app.schemas.notifications import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(user: CurrentUser, session: Session, unseen: bool = True):
    not_implemented()


@router.post("/{notification_id}/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_seen(notification_id: int, user: CurrentUser, session: Session):
    not_implemented()