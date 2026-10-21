from datetime import datetime

from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    note_id: int
    title: str
    occurrence_starts_at: datetime
    created_at: datetime
    seen_at: datetime | None