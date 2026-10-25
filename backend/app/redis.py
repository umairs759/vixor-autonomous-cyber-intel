"""VIXOR — Redis client dependency.

Provides a Redis client for rate limiting, Celery broker, and pub/sub.
"""

import redis

from app.config import get_settings


def get_redis_client() -> redis.Redis:
    """Create a Redis client from settings."""
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


# For dependency injection in routes
get_redis = get_redis_client
