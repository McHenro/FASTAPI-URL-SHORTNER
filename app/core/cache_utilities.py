import logging
from typing import Optional
from app.core.config import settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

redis: Optional[Redis] = None


async def init_redis() -> None:
    global redis
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
        decode_responses=True,
    )
    logger.info("Redis connection initialized")


async def close_redis() -> None:
    global redis
    if redis:
        await redis.aclose()
        redis = None
    logger.info("Redis connection closed")


async def _get_redis() -> Redis:
    if redis is None:
        raise RuntimeError("Redis not initialized")
    return redis


async def get_cache(key: str) -> Optional[str]:
    r = await _get_redis()
    return await r.get(key)


async def set_cache(key: str, value: str, ttl: int = 300) -> None:
    r = await _get_redis()
    await r.set(key, value, ex=ttl)


async def delete_cache(key: str) -> None:
    r = await _get_redis()
    await r.delete(key)


def url_cache_key(short_code: str, **kwargs) -> str:
    """Generate a Redis cache key for URL short code lookups.

    Creates a namespaced cache key using the provided short code.
    This helps avoid key collisions and keeps cache entries organized.

    Args:
        short_code: The short code associated with the URL.

    Returns:
        A string representing the Redis cache key.
    """
    return f"url_shortcode:{short_code}"
