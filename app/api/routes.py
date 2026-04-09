"""FastAPI API routes for the URL shortener service.

Exposes three endpoints:
- POST /shorten: Accepts a long URL and returns a generated short code with the original URL.
- GET /urls: Returns all stored URL mappings (short codes + long URLs).
- GET /{short_code}: Redirects the client to the original long URL if the short code exists.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.url_schema import URLCreate, URLResponse
from app.services.url_service import (
    create_short_url_service,
    get_all_urls_service,
    get_long_url_service,
)
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.post("/shorten", response_model=URLResponse)
def create_short_url(p: URLCreate, db: Session = Depends(get_db)) -> URLResponse:
    """Create a short URL code for a provided long URL.

    Args:
        p: Pydantic model containing the `long_url` to shorten.
        db: SQLAlchemy DB session dependency.

    Returns:
        URLResponse: The persisted URL record containing the `short_code` and `long_url`.
    """
    url = create_short_url_service(db, p.long_url)
    return url


# NEW ENDPOINT — must be defined BEFORE /{short_code} so FastAPI matches /urls
# exactly rather than treating "urls" as a short code.
@router.get("/urls", response_model=list[URLResponse])
def list_all_urls(db: Session = Depends(get_db)) -> list[URLResponse]:
    """Return every stored URL mapping.

    Useful for inspecting all short codes and their corresponding long URLs.

    Args:
        db: SQLAlchemy DB session dependency.

    Returns:
        A list of all URL records, each containing `short_code` and `long_url`.
    """
    return get_all_urls_service(db)


# SCALABILITY — Async: converted to async def so the event loop is not blocked.
# The DB calls below are still synchronous (SQLAlchemy sync). When you switch to
# an async ORM (asyncpg / SQLAlchemy async), replace the db.query(...) calls with:
#   url = await db.execute(select(URL).where(URL.short_code == short_code))
@router.get("/{short_code}")
async def redirect_to_long_url(short_code: str, db: Session = Depends(get_db)):
    """Redirect to the original long URL for the given short code.

    Args:
        short_code: The short code to resolve.
        db: SQLAlchemy DB session dependency.

    Raises:
        HTTPException: 404 if the short code does not exist.

    Returns:
        RedirectResponse: A 307 redirect to the original `long_url`.
    """
    # SCALABILITY — Redis Caching: hit the cache before the DB
    # TODO: cached_url = redis_client.get(short_code)
    # TODO: if cached_url:
    # TODO:     return RedirectResponse(url=cached_url)  # Fast path — no DB query

    url = get_long_url_service(db, short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # TODO: Replace SQLAlchemy sync with async ORM (e.g. asyncpg) when ready:
    # TODO: url = await db.execute(select(URL).where(URL.short_code == short_code))

    return RedirectResponse(url=url.long_url)

