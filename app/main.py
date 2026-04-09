"""Entry point for the URL shortener FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from app.core.database import Base, engine
from app.api.routes import router

# Create all database tables on startup (no-op if they already exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")

app.include_router(router)
