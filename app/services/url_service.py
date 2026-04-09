"""Business logic for creating and resolving shortened URLs.

This module contains small service helpers used by the API layer. It is kept
framework-agnostic and operates on SQLAlchemy sessions and models only.
"""

import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from app.models.url import URL


def generate_short_code(length: int = 6) -> str:
    """Generate a pseudo-random alphanumeric short code.

    Args:
        length: Number of characters in the generated code (default: 6).

    Returns:
        A random alphanumeric string of the requested length.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def create_short_url_service(db: Session, long_url: str) -> URL:
    """Create and persist a new URL mapping with a collision-safe short code.

    Keeps regenerating a short code until one is found that does not already
    exist in the database, preventing uniqueness constraint violations.

    Args:
        db: Active SQLAlchemy session.
        long_url: The original URL to shorten.

    Returns:
        The persisted `URL` model instance.
    """
    # SCALABILITY — Collision Prevention: regenerate until a unique code is found
    while True:
        short_code = generate_short_code()
        # TODO: Check Redis cache here too before hitting DB
        # cached = redis_client.get(short_code)
        # if cached:
        #     continue  # Code is in use — try again
        exists = db.query(URL).filter(URL.short_code == short_code).first()
        if not exists:
            break

    new_url = URL(long_url=long_url, short_code=short_code)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)
    return new_url


def get_long_url_service(db: Session, short_code: str) -> Optional[URL]:
    """Retrieve the stored URL mapping by its short code.

    Args:
        db: Active SQLAlchemy session.
        short_code: The short code to look up.

    Returns:
        The `URL` instance if found, otherwise `None`.
    """
    # SCALABILITY — Redis Caching: check cache before hitting the DB
    # TODO: cached_url = redis_client.get(short_code)
    # TODO: if cached_url:
    # TODO:     return cached_url  # Fast path — skips DB entirely

    url = db.query(URL).filter(URL.short_code == short_code).first()

    # TODO: Store in Redis so the next request skips the DB
    # TODO: if url:
    # TODO:     redis_client.setex(short_code, 3600, url.long_url)  # TTL: 1 hour

    return url


def get_all_urls_service(db: Session) -> list[URL]:
    """Retrieve all stored URL mappings.

    Useful for admin inspection, extracting short codes, or auditing long URLs.

    Args:
        db: Active SQLAlchemy session.

    Returns:
        A list of all `URL` model instances.
    """
    return db.query(URL).all()
