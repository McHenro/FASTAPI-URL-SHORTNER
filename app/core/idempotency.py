"""
Idempotency key support for POST /links.

Flow:
  1. Client generates a UUID and sends it in the Idempotency-Key header.
  2. First request → process normally, store result in Redis with a 24 h TTL.
  3. Retry with the same key → return the stored result, skip all DB writes.

Keys live in their own Redis namespace (idem:) so they never clash with the
URL cache keys (url_shortcode:).
"""

import json
import logging
from typing import Optional

from app.core.cache_utilities import get_cache, set_cache

logger = logging.getLogger(__name__)

_TTL = 86400        # 24 hours
_PREFIX = "idem:"   # namespace — avoids collision with url_shortcode: keys


async def get_idempotent_response(key: str) -> Optional[dict]:
    """Return the cached response for this key, or None on a first-time request."""
    raw = await get_cache(f"{_PREFIX}{key}")
    if raw:
        logger.info("Idempotency hit: %s", key)
        return json.loads(raw)
    return None


async def store_idempotent_response(key: str, data: dict) -> None:
    """Persist the response after a successful DB write.

    Always call this AFTER the write succeeds. 
    """
    await set_cache(f"{_PREFIX}{key}", json.dumps(data), ttl=_TTL)
    logger.info("Idempotency key stored: %s (TTL %ds)", key, _TTL)
