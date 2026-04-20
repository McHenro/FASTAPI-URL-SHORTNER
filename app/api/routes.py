"""FastAPI API routes for the URL shortener service.

All handlers are async. DB sessions are AsyncSession (asyncpg-backed).
Redis is checked first on the redirect hot path before hitting the DB.

Endpoints:
- POST /links               create a short link
- GET  /links               list all stored links
- GET  /links/{short_code}  redirect to original URL (307)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.url_schema import URLCreate, URLResponse
from app.services.url_service import (
    create_short_url_service,
    get_all_urls_service,
    get_long_url_service,
    delete_url_service,
    redis_client,
)
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.post("/links", response_model=URLResponse)
async def create_short_url(p: URLCreate, db: AsyncSession = Depends(get_db)) -> URLResponse:
    """Create a short URL code for a provided long URL.

    Args:
        p: Pydantic model containing the long_url to shorten.
        db: Async SQLAlchemy DB session dependency.

    Returns:
        URLResponse: The persisted URL record containing short_code and long_url.
    """
    url = await create_short_url_service(db, p.long_url)
    return url


@router.get("/links", response_model=List[URLResponse])
async def list_all_urls(db: AsyncSession = Depends(get_db)) -> List[URLResponse]:
    """Return every stored URL mapping.

    Args:
        db: Async SQLAlchemy DB session dependency.

    Returns:
        A list of all URL records, each containing short_code and long_url.
    """
    return await get_all_urls_service(db)


@router.get("/links/{short_code}")
async def redirect_to_long_url(short_code: str, db: AsyncSession = Depends(get_db)):
    """Redirect to the original long URL for the given short code.

    Checks Redis first (fast path). Falls back to DB on a cache miss,
    then writes the result to Redis for subsequent requests.

    Args:
        short_code: The short code to resolve.
        db: Async SQLAlchemy DB session dependency.

    Raises:
        HTTPException: 404 if the short code does not exist.

    Returns:
        RedirectResponse: A 307 redirect to the original long_url.
    """
    # Fast path: Redis hit skips the DB entirely
    cached_url = redis_client.get(short_code)
    if cached_url:
        return RedirectResponse(url=cached_url)

    # Cache miss: query DB (service also writes result back to Redis)
    url = await get_long_url_service(db, short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    return RedirectResponse(url=url.long_url)


@router.delete("/links/{short_code}")
async def delete_a_url(short_code: str, db: AsyncSession = Depends(get_db)):
   
    return await delete_url_service(db, short_code)
