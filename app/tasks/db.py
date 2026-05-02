"""Synchronous SQLAlchemy session for use inside Celery tasks.

Celery workers are not async — they run in a plain thread, so they need a
regular (sync) engine and session, not the async ones used by FastAPI.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
_SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@contextmanager
def get_sync_db():
    """Yield a sync SQLAlchemy session and close it when done."""
    db: Session = _SessionFactory()
    try:
        yield db
    finally:
        db.close()
