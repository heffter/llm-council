"""
Rate limiting backends for distributed and single-instance deployments.

Provides abstract RateLimiter interface with two implementations:
- MemoryRateLimiter: In-memory store for single-instance deployments
- RedisRateLimiter: Redis-backed store for distributed deployments

Configuration:
- RATE_LIMIT_BACKEND: "memory" (default) or "redis"
- REDIS_URL: Redis connection URL (required if backend is "redis")
"""

import os
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Any
from enum import Enum

from .logger import get_logger


class RateLimitBackend(Enum):
    """Available rate limiting backends."""
    MEMORY = "memory"
    REDIS = "redis"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at_ms: int
    retry_after_seconds: Optional[int] = None

    def __post_init__(self):
        if not self.allowed and self.retry_after_seconds is None:
            now_ms = int(time.time() * 1000)
            self.retry_after_seconds = max(1, (self.reset_at_ms - now_ms) // 1000)


class RateLimiter(ABC):
    """Abstract rate limiter interface."""

    @abstractmethod
    async def check_limit(
        self, key: str, window_ms: int, max_requests: int
    ) -> RateLimitResult:
        """
        Check rate limit and increment counter.

        Args:
            key: Rate limit key (e.g., "token:xxx" or "ip:xxx")
            window_ms: Window size in milliseconds
            max_requests: Maximum requests allowed per window

        Returns:
            RateLimitResult with allowed status and metadata
        """
        pass

    @abstractmethod
    async def get_remaining(self, key: str, window_ms: int, max_requests: int) -> int:
        """
        Get remaining requests for a key without incrementing.

        Args:
            key: Rate limit key
            window_ms: Window size in milliseconds
            max_requests: Maximum requests allowed per window

        Returns:
            Number of remaining requests in current window
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of the rate limiter backend.

        Returns:
            Dictionary with health status information
        """
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the name of this backend."""
        pass


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for single-instance deployments."""

    def __init__(self):
        self._store: Dict[str, Tuple[int, int]] = {}  # key -> (count, reset_at_ms)

    async def check_limit(
        self, key: str, window_ms: int, max_requests: int
    ) -> RateLimitResult:
        now_ms = int(time.time() * 1000)

        if key in self._store:
            count, reset_at = self._store[key]

            # Reset if window expired
            if now_ms > reset_at:
                count = 0
                reset_at = now_ms + window_ms
        else:
            count = 0
            reset_at = now_ms + window_ms

        # Increment count
        count += 1
        self._store[key] = (count, reset_at)

        # Check if over limit
        allowed = count <= max_requests
        remaining = max(0, max_requests - count)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at_ms=reset_at
        )

    async def get_remaining(self, key: str, window_ms: int, max_requests: int) -> int:
        now_ms = int(time.time() * 1000)

        if key not in self._store:
            return max_requests

        count, reset_at = self._store[key]

        # Window expired, full quota available
        if now_ms > reset_at:
            return max_requests

        return max(0, max_requests - count)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "backend": "memory",
            "status": "healthy",
            "keys_tracked": len(self._store)
        }

    @property
    def backend_name(self) -> str:
        return "memory"


class RedisRateLimiter(RateLimiter):
    """
    Redis-backed rate limiter for distributed deployments.

    Uses atomic INCR/EXPIRE for fixed window rate limiting.
    Includes connection pooling, retry logic, and graceful fallback.
    """

    def __init__(self, redis_url: str, fallback_limiter: Optional[RateLimiter] = None):
        self._redis_url = redis_url
        self._redis_client = None
        self._fallback = fallback_limiter or MemoryRateLimiter()
        self._in_fallback_mode = False
        self._last_error: Optional[str] = None
        self._connection_attempts = 0
        self._max_retries = 3
        self._retry_delay_base = 0.1  # 100ms base delay
        self._logger = get_logger("redis_rate_limiter")

    async def _get_client(self):
        """Get or create Redis client with lazy initialization."""
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            await self._redis_client.ping()
            self._in_fallback_mode = False
            self._last_error = None
            self._logger.info("Redis connection established")
            return self._redis_client
        except ImportError:
            self._last_error = "redis package not installed"
            self._in_fallback_mode = True
            self._logger.error("Redis package not installed, using fallback")
            return None
        except Exception as e:
            self._last_error = str(e)
            self._in_fallback_mode = True
            self._logger.error("Redis connection failed", error=str(e))
            return None

    async def _execute_with_retry(self, operation):
        """Execute Redis operation with exponential backoff retry."""
        last_error = None

        for attempt in range(self._max_retries):
            try:
                client = await self._get_client()
                if client is None:
                    # No client available, use fallback
                    return None

                result = await operation(client)
                # Success - reset error state
                if self._in_fallback_mode:
                    self._in_fallback_mode = False
                    self._logger.info("Redis recovered from fallback mode")
                return result

            except Exception as e:
                last_error = e
                self._last_error = str(e)

                if attempt < self._max_retries - 1:
                    delay = self._retry_delay_base * (2 ** attempt)
                    self._logger.warn(
                        "Redis operation failed, retrying",
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
                else:
                    # All retries failed, enter fallback mode
                    self._in_fallback_mode = True
                    self._logger.error(
                        "Redis operation failed after all retries, entering fallback mode",
                        error=str(e)
                    )

        return None

    async def check_limit(
        self, key: str, window_ms: int, max_requests: int
    ) -> RateLimitResult:
        # Calculate window key
        now_ms = int(time.time() * 1000)
        window_start = (now_ms // window_ms) * window_ms
        redis_key = f"rate_limit:{key}:{window_start}"
        reset_at = window_start + window_ms

        async def redis_incr(client):
            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.pexpire(redis_key, window_ms + 1000)  # Extra second for safety
            results = await pipe.execute()
            return results[0]  # Returns new count

        count = await self._execute_with_retry(redis_incr)

        if count is None:
            # Fallback to memory limiter
            return await self._fallback.check_limit(key, window_ms, max_requests)

        allowed = count <= max_requests
        remaining = max(0, max_requests - count)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at_ms=reset_at
        )

    async def get_remaining(self, key: str, window_ms: int, max_requests: int) -> int:
        now_ms = int(time.time() * 1000)
        window_start = (now_ms // window_ms) * window_ms
        redis_key = f"rate_limit:{key}:{window_start}"

        async def redis_get(client):
            count = await client.get(redis_key)
            return int(count) if count else 0

        count = await self._execute_with_retry(redis_get)

        if count is None:
            return await self._fallback.get_remaining(key, window_ms, max_requests)

        return max(0, max_requests - count)

    async def health_check(self) -> Dict[str, Any]:
        result = {
            "backend": "redis",
            "redis_url": self._redis_url.split("@")[-1] if "@" in self._redis_url else self._redis_url,
            "in_fallback_mode": self._in_fallback_mode,
            "last_error": self._last_error,
        }

        try:
            client = await self._get_client()
            if client is None:
                result["status"] = "degraded"
                result["message"] = "Using fallback memory limiter"
            else:
                await client.ping()
                result["status"] = "healthy"
                info = await client.info("clients")
                result["connected_clients"] = info.get("connected_clients", 0)
        except Exception as e:
            result["status"] = "degraded"
            result["message"] = f"Health check failed: {e}"

        return result

    @property
    def backend_name(self) -> str:
        if self._in_fallback_mode:
            return "redis (fallback: memory)"
        return "redis"


# =============================================================================
# Configuration and Factory
# =============================================================================

# Configuration from environment
RATE_LIMIT_BACKEND = os.getenv("RATE_LIMIT_BACKEND", "memory").lower()
REDIS_URL = os.getenv("REDIS_URL", "")

# Validate backend configuration
if RATE_LIMIT_BACKEND not in ("memory", "redis"):
    raise ValueError(
        f"Invalid RATE_LIMIT_BACKEND: {RATE_LIMIT_BACKEND}. "
        "Must be 'memory' or 'redis'"
    )

if RATE_LIMIT_BACKEND == "redis" and not REDIS_URL:
    raise ValueError(
        "REDIS_URL is required when RATE_LIMIT_BACKEND is 'redis'. "
        "Example: redis://localhost:6379/0"
    )


# Global rate limiter instance (lazy initialization)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create the configured rate limiter instance.

    Returns:
        Configured RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is not None:
        return _rate_limiter

    logger = get_logger("rate_limiter")

    if RATE_LIMIT_BACKEND == "redis":
        logger.info("Initializing Redis rate limiter", redis_url=REDIS_URL)
        _rate_limiter = RedisRateLimiter(REDIS_URL)
    else:
        logger.info("Initializing memory rate limiter")
        _rate_limiter = MemoryRateLimiter()

    return _rate_limiter


def get_rate_limit_config() -> Dict[str, Any]:
    """
    Get current rate limiter configuration info.

    Returns:
        Dictionary with backend configuration
    """
    return {
        "backend": RATE_LIMIT_BACKEND,
        "redis_configured": bool(REDIS_URL),
    }
