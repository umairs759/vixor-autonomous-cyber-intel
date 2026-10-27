"""VIXOR — Redis rate limiting (T-009).

Sliding-window rate limiter using Redis. Tracks per-key request counts
with expiry windows. Used for auth endpoints and scan creation.
"""

import time

import redis


class RateLimiter:
    """Sliding-window rate limiter backed by Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """Check if a request is allowed under the rate limit.

        Returns (allowed, remaining_requests).
        """
        now = time.time()
        window_start = now - window_seconds

        pipe = self.redis.pipeline()
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries in window
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set expiry on the key
        pipe.expire(key, window_seconds)
        results = pipe.execute()  # type: ignore[no-untyped-call]

        current_count = results[1]
        allowed = current_count < limit
        remaining = max(0, limit - current_count) if allowed else 0

        if not allowed:
            # Remove the request we just added since it's not allowed
            self.redis.zrem(key, str(now))

        return allowed, remaining
