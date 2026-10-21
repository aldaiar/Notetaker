from sqlalchemy import text
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import VersionConflict
from app.schemas.notes import NoteConflict, NoteRead


from app.db.database import engine
from app.db.base import Base
from app.db import models
from app.routers import (
    calendar, events, notes, notifications, occurrences, tags, trash, users,
)
from app.api.auth import router as auth_router
from app.api.register import router as register_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.exception_handler(VersionConflict)
async def version_conflict_handler(request: Request, exc: VersionConflict):
    body = NoteConflict(current=NoteRead.model_validate(exc.note))
    return JSONResponse(status_code=409, content=body.model_dump(mode="json"))

app.include_router(auth_router)
app.include_router(register_router)

for r in (users, notes, occurrences, trash, tags, calendar, notifications, events):
    app.include_router(r.router)





@app.get("/health/db", tags=["Health"])
async def database_health():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))

    return {"database": result.scalar_one()}
