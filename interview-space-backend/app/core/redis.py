import logging
from typing import AsyncGenerator, Optional

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    global _redis_client

    if _redis_client is not None:
        await _redis_client.ping()
        return

    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        raise

    _redis_client = client
    logger.info("Redis connection initialized")


async def close_redis() -> None:
    global _redis_client

    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    if _redis_client is not None:
        yield _redis_client
        return

    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
