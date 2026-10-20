from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine

app = FastAPI()


@app.get("/health/db")
async def database_health():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        return {"database": result.scalar_one()}