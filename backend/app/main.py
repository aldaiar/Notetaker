from sqlalchemy import text
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import engine
from app.db.base import Base
from app.db import models
from app.api.register import router as register_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(register_router)


@app.get("/health/db", tags=["Health"])
async def database_health():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))

    return {"database": result.scalar_one()}
