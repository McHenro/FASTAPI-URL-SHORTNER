"""Entry point for the URL shortener FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import Base, engine
from app.api.routes import v1_router
from app.api.webhook_routes import webhook_router
from app.core.cache_utilities import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and open Redis connection on startup; close Redis on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.include_router(v1_router)
app.include_router(webhook_router)
