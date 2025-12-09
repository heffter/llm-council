"""Authentication and rate limiting middleware."""

import os
import time
from typing import Optional, Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


# Configuration from environment
SHARED_WRITE_TOKEN = os.getenv("SHARED_WRITE_TOKEN")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_WINDOW_MS = int(os.getenv("RATE_LIMIT_WINDOW_MS", "60000"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))


class RateLimitStore:
    """In-memory rate limit tracking store."""

    def __init__(self):
        """Initialize empty rate limit store."""
        self._store: Dict[str, Tuple[int, int]] = {}  # key -> (count, reset_at_ms)

    def check_and_increment(
        self, key: str, window_ms: int, max_requests: int
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit and increment counter.

        Args:
            key: Rate limit key (token or IP)
            window_ms: Window size in milliseconds
            max_requests: Maximum requests per window

        Returns:
            Tuple of (allowed, remaining, reset_at_ms)
        """
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

        return allowed, remaining, reset_at


# Global rate limit store
_rate_limit_store = RateLimitStore()


async def shared_secret_middleware(request: Request, call_next):
    """
    Middleware to enforce shared secret authentication on write endpoints.

    Checks for X-Shared-Token header and validates against SHARED_WRITE_TOKEN.
    Only active if SHARED_WRITE_TOKEN is set in environment.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response from next handler or 401 error
    """
    # Only enforce if token is configured
    if not SHARED_WRITE_TOKEN:
        return await call_next(request)

    # Only check write endpoints (POST, PUT, PATCH, DELETE)
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return await call_next(request)

    # Check for token header
    token = request.headers.get("X-Shared-Token")

    if not token or token != SHARED_WRITE_TOKEN:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: invalid or missing shared token"}
        )

    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to enforce rate limiting per token or IP.

    Uses in-memory sliding window for single-node deployments.
    Only active if RATE_LIMIT_ENABLED=true in environment.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response from next handler or 429 error
    """
    # Only enforce if enabled
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    # Determine rate limit key (prefer token, fallback to IP)
    token = request.headers.get("X-Shared-Token")
    if token:
        rate_key = f"token:{token}"
    else:
        # Get client IP (handle proxy headers)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            # Take first IP if multiple
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        rate_key = f"ip:{client_ip}"

    # Check rate limit
    allowed, remaining, reset_at = _rate_limit_store.check_and_increment(
        rate_key, RATE_LIMIT_WINDOW_MS, RATE_LIMIT_MAX_REQUESTS
    )

    if not allowed:
        # Calculate retry-after in seconds
        now_ms = int(time.time() * 1000)
        retry_after = max(1, (reset_at - now_ms) // 1000)

        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at // 1000)
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)

    # Add headers if it's a standard response
    if hasattr(response, 'headers'):
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at // 1000)

    return response
