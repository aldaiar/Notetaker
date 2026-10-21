from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.tags import TagRead


class OccurrenceRead(BaseModel):
    note_id: int
    occurrence_start: datetime  # исходное время вхождения в серии (идентификатор вхождения)
    starts_at: datetime         # фактическое время (отличается, если вхождение перенесли)
    title: str
    body: str | None
    is_active: bool
    is_recurring: bool
    is_exception: bool
    tags: list[TagRead]
    version: int


class UpcomingRead(BaseModel):
    server_time: datetime
    today: list[OccurrenceRead]
    week: list[OccurrenceRead]
    past: list[OccurrenceRead]
    past_next_cursor: str | None = None