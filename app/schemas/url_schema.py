"""Pydantic schemas for request/response validation in the URL shortener.

These models define the shape of data accepted by and returned from the API
endpoints. They provide runtime validation and automatic documentation for
FastAPI.
"""

from pydantic import BaseModel


class URLCreate(BaseModel):
    """Payload for creating a short URL.

    Attributes:
        long_url: The original URL to shorten.
    """

    long_url: str


class URLResponse(BaseModel):
    """Response model representing a stored URL mapping.

    Attributes:
        short_code: The generated short identifier (e.g., "X9D7FF").
        long_url: The original URL to which clients will be redirected.
    """

    short_code: str
    long_url: str

    class Config:
        # Allow creating this schema directly from ORM objects (e.g., SQLAlchemy models)
        from_attributes = True
