from fastapi import APIRouter, status

from app.deps import CurrentUser, Session
from app.schemas.tags import TagCreate, TagRead, TagUpdate
from app.api import tags as service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(user: CurrentUser, session: Session):
    return await service.list_tags(session, user.id)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(body: TagCreate, user: CurrentUser, session: Session):
    return await service.create_tag(session, user.id, body)


@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(tag_id: int, body: TagUpdate, user: CurrentUser, session: Session):
    return await service.update_tag(session, user.id, tag_id, body)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, user: CurrentUser, session: Session):
    await service.delete_tag(session, user.id, tag_id)