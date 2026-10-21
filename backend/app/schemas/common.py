from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None  # непрозрачный keyset-курсор; None = конец списка


class VersionBody(BaseModel):
    """Тело для activate/deactivate/restore: версия нужна для optimistic locking."""
    version: int