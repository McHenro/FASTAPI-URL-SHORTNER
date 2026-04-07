"""Database setup and session management for the URL shortener app.

This module configures the SQLAlchemy engine, session factory, and provides the
`get_db` dependency used in FastAPI routes to inject a scoped database session.

Environment:
    - Expects `DATABASE_URL` to be defined in the environment (read from `.env`).

Notes:
    - The engine and session here are synchronous. If you plan to migrate to
      async endpoints, use `sqlalchemy.ext.asyncio` and an async session pattern.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine  # Imported for potential async migration
from dotenv import load_dotenv

# Load environment variables from a `.env` file if present.
load_dotenv()

# Connection string for the database, e.g., "postgresql://user:password@localhost/dbname"
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a synchronous SQLAlchemy engine bound to the connection string.
engine = create_engine(DATABASE_URL)

# Configure a session factory. `autocommit` and `autoflush` are disabled for explicit control.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for SQLAlchemy models to inherit from.
Base = declarative_base()


def get_db():
    """Yield a database session and ensure it is closed after use.

    This is designed to be used as a FastAPI dependency, which provides a DB
    session to path operation functions and guarantees cleanup.

    Yields:
        Session: A SQLAlchemy session bound to the configured engine.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


