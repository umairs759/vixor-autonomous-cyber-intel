"""VIXOR — Redis client dependency.

Provides a Redis client for rate limiting, Celery broker, and pub/sub.
"""

import redis
from redis import Redis

from app.config import get_settings


def get_redis_client() -> Redis:
    """Create a Redis client from settings."""
    settings = get_settings()
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)  # type: ignore[no-untyped-call]
    return client  # type: ignore[no-any-return]


# For dependency injection in routes
get_redis = get_redis_client
