"""SQLAlchemy ORM models for the URL shortener application."""

from sqlalchemy import Column, Integer, String
from app.core.database import Base


class URL(Base):
    """Represents a mapping from a generated short code to a long URL.

    Attributes:
        id: Auto-incrementing primary key.
        long_url: The original URL to redirect to.
        short_code: The generated short identifier (e.g., "X9D7FF").
    """

    __tablename__ = "urls"

    # Primary key for the URL mapping
    id = Column(Integer, primary_key=True, index=True)

    # Target URL that the short code will redirect to
    long_url = Column(String, nullable=False)

    # Unique short code for quick lookup and redirection
    short_code = Column(String, unique=True, index=True)

