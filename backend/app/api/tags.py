from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tag
from app.schemas.tags import TagCreate, TagUpdate


async def get_tag(session: AsyncSession, user_id: int, tag_id: int) -> Tag:
    tag = await session.scalar(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    if tag is None:  # чужой тег тоже 404, чтобы не раскрывать его существование
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тег не найден")
    return tag


async def list_tags(session: AsyncSession, user_id: int) -> list[Tag]:
    result = await session.scalars(
        select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return list(result)


async def create_tag(session: AsyncSession, user_id: int, data: TagCreate) -> Tag:
    tag = Tag(user_id=user_id, name=data.name, color=data.color)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Тег с таким именем уже существует")
    await session.refresh(tag)
    return tag


async def update_tag(
    session: AsyncSession, user_id: int, tag_id: int, data: TagUpdate
) -> Tag:
    tag = await get_tag(session, user_id, tag_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(tag, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Тег с таким именем уже существует")
    await session.refresh(tag)
    return tag


async def delete_tag(session: AsyncSession, user_id: int, tag_id: int) -> None:
    await get_tag(session, user_id, tag_id)  # проверка владельца и 404
    # Bulk delete, а не session.delete(tag): ORM при удалении объекта с many-to-many
    # сначала лениво грузит tag.notes, а в async это даёт MissingGreenlet.
    # Строки note_tags удалит БД каскадом.
    await session.execute(delete(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    await session.commit()