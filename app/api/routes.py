"""FastAPI API routes for the URL shortener service.

Exposes two endpoints:
- POST /shorten: Accepts a long URL and returns a generated short code with the original URL.
- GET /{short_code}: Redirects the client to the original long URL if the short code exists.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.url_schema import URLCreate, URLResponse
from app.services.url_service import create_short_url_service, get_long_url_service
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


@router.get("/{short_code}")
def redirect_to_long_url(short_code: str, db: Session = Depends(get_db)):
    """Redirect to the original long URL for the given short code.

    Args:
        short_code: The short code to resolve.
        db: SQLAlchemy DB session dependency.

    Raises:
        HTTPException: 404 if the short code does not exist.

    Returns:
        RedirectResponse: A 307 redirect to the original `long_url`.
    """
    url = get_long_url_service(db, short_code)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Use Starlette's RedirectResponse to send the client to the original URL.
    return RedirectResponse(url=url.long_url)

