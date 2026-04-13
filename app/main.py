"""Entry point for the URL shortener FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import Base, engine
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup, then yield control to the app."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.include_router(router)
