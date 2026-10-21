from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.common import ORMModel

TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]


class TagCreate(BaseModel):
    name: TagName
    color: HexColor = "#888888"


class TagUpdate(BaseModel):
    name: TagName | None = None
    color: HexColor | None = None


class TagRead(ORMModel):
    id: int
    name: str
    color: str