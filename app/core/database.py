"""Database setup and session management for the URL shortener app.

Fully async: uses SQLAlchemy's asyncio extension with the asyncpg driver.

Environment:
    - DATABASE_URL must use the asyncpg scheme:
      postgresql+asyncpg://user:password@host/dbname
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Async engine — delegates actual I/O to asyncpg under the hood
engine = create_async_engine(DATABASE_URL, echo=False)

# Async session factory.
# expire_on_commit=False keeps attribute access working after commit
# without needing an extra await db.refresh().
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base class all ORM models inherit from
Base = declarative_base()


async def get_db():
    """Yield an async database session and guarantee it is closed after use.

    FastAPI awaits the generator automatically when used as a Depends().

    Yields:
        AsyncSession: An async-capable SQLAlchemy session.
    """
    async with AsyncSessionLocal() as db:
        yield db
