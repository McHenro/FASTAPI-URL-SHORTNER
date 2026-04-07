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

    Uses upper/lowercase letters and digits. Collisions are possible but
    unlikely for small datasets. For production, consider enforcing uniqueness
    by checking the database or using a more robust strategy.

    Args:
        length: Number of characters in the generated code (default: 6).

    Returns:
        A random alphanumeric string of the requested length.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def create_short_url_service(db: Session, long_url: str) -> URL:
    """Create and persist a new URL mapping with a generated short code.

    Note:
        This implementation does not currently check for collisions. For a
        production system, add a retry loop to regenerate the code when a
        uniqueness constraint violation occurs.

    Args:
        db: Active SQLAlchemy session.
        long_url: The original URL to shorten.

    Returns:
        The persisted `URL` model instance.
    """
    short_code = generate_short_code()
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
    return db.query(URL).filter(URL.short_code == short_code).first()
