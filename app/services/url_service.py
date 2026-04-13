"""Business logic for creating and resolving shortened URLs.

All service functions are async and use SQLAlchemy's async ORM (asyncpg driver).
Redis is used as a write-through cache for the redirect hot path.
"""

import random
import string
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.url import URL
import redis

# Redis client — redis-py is synchronous, which is fine for lightweight cache calls
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


def generate_short_code(length: int = 6) -> str:
    """Generate a pseudo-random alphanumeric short code.

    Pure CPU work — no I/O, so no async needed here.

    Args:
        length: Number of characters in the generated code (default: 6).

    Returns:
        A random alphanumeric string of the requested length.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


async def create_short_url_service(db: AsyncSession, long_url: str) -> URL:
    """Create and persist a new URL mapping with a collision-safe short code.

    Keeps generating codes until one that does not already exist in the DB is found.

    Args:
        db: Active async SQLAlchemy session.
        long_url: The original URL to shorten.

    Returns:
        The persisted URL model instance.
    """
    # Collision Prevention: query the DB until a unique code is found
    while True:
        short_code = generate_short_code()
        result = await db.execute(select(URL).where(URL.short_code == short_code))
        if not result.scalar_one_or_none():
            break

    new_url = URL(long_url=long_url, short_code=short_code)
    db.add(new_url)
    await db.commit()
    await db.refresh(new_url)
    return new_url


async def get_long_url_service(db: AsyncSession, short_code: str) -> Optional[URL]:
    """Retrieve the stored URL mapping by its short code.

    Writes to Redis on a DB hit so the next redirect is served from cache.
    Always returns a URL object (or None) — never a raw string.

    Args:
        db: Active async SQLAlchemy session.
        short_code: The short code to look up.

    Returns:
        The URL instance if found, otherwise None.
    """
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()

    # Write-through: populate Redis so the next redirect skips the DB entirely
    if url:
        redis_client.setex(short_code, 3600, url.long_url)  # TTL: 1 hour

    return url


async def get_all_urls_service(db: AsyncSession) -> List[URL]:
    """Retrieve all stored URL mappings.

    Args:
        db: Active async SQLAlchemy session.

    Returns:
        A list of all URL model instances.
    """
    result = await db.execute(select(URL))
    return result.scalars().all()
