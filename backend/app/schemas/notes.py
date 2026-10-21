from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator, model_validator

from app.schemas.common import ORMModel
from app.schemas.tags import TagRead

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ReminderOffset = Literal[10, 60, 1440]  # за 10 минут, за час, за день


class RecurrenceFreq(StrEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Recurrence(BaseModel):
    freq: RecurrenceFreq
    until: date | None = None  # дата окончания повторов, None = бессрочно


def _unique(values: list) -> list:
    if len(set(values)) != len(values):
        raise ValueError("Значения не должны повторяться")
    return values


class NoteCreate(BaseModel):
    title: Title
    body: str = ""
    starts_at: AwareDatetime
    is_active: bool = True
    tag_ids: list[int] = []
    reminders: list[ReminderOffset] = []
    recurrence: Recurrence | None = None

    _uniq_tags = field_validator("tag_ids")(_unique)
    _uniq_reminders = field_validator("reminders")(_unique)


class NoteUpdate(BaseModel):
    """
    PATCH. Применять через model_dump(exclude_unset=True):
    - поле не передано -> не меняется;
    - recurrence: null -> повтор снимается;
    - title, starts_at, tag_ids, reminders явным null быть не могут.
    """
    version: int = Field(ge=1)
    title: Title | None = None
    body: str | None = None
    starts_at: AwareDatetime | None = None
    tag_ids: list[int] | None = None
    reminders: list[ReminderOffset] | None = None
    recurrence: Recurrence | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        for f in ("title", "body", "starts_at", "tag_ids", "reminders"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} не может быть null")
        return self

    @field_validator("tag_ids", "reminders")
    @classmethod
    def unique_lists(cls, v):
        return _unique(v) if v is not None else v


class NoteRead(ORMModel):
    id: int
    title: str
    body: str | None
    starts_at: datetime
    is_active: bool
    recurrence: Recurrence | None
    tags: list[TagRead]
    reminders: list[int]
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @model_validator(mode="before")
    @classmethod
    def from_model(cls, v):
        """Собирает NoteRead из ORM-модели (плоские recurrence_* -> вложенный объект)."""
        if isinstance(v, dict):
            return v
        return {
            "id": v.id,
            "title": v.title,
            "body": v.body,
            "starts_at": v.starts_at,
            "is_active": v.is_active,
            "recurrence": (
                {"freq": v.recurrence_freq, "until": v.recurrence_until}
                if v.recurrence_freq else None
            ),
            "tags": v.tags,
            "reminders": sorted(r.offset_minutes for r in v.reminders),
            "version": v.version,
            "created_at": v.created_at,
            "updated_at": v.updated_at,
            "deleted_at": v.deleted_at,
        }


class NoteConflict(BaseModel):
    """Тело ответа 409: клиент показывает, что версия изменилась, и даёт выбрать."""
    detail: str = "Заметка была изменена"
    current: NoteRead


# --- вхождения повторяющихся заметок ---

class OccurrenceScope(StrEnum):
    this = "this"
    following = "following"


class OccurrenceUpdate(BaseModel):
    scope: OccurrenceScope
    version: int = Field(ge=1)  # версия серии (notes.version)
    title: Title | None = None
    body: str | None = None
    starts_at: AwareDatetime | None = None  # новое время (перенос)