"""Authentication and rate limiting middleware."""

import os
from fastapi import Request
from fastapi.responses import JSONResponse

from .rate_limiter import get_rate_limiter


# Configuration from environment
SHARED_WRITE_TOKEN = os.getenv("SHARED_WRITE_TOKEN")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_WINDOW_MS = int(os.getenv("RATE_LIMIT_WINDOW_MS", "60000"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))


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

    Uses configurable backend (memory or Redis) based on RATE_LIMIT_BACKEND.
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

    # Get rate limiter and check limit
    limiter = get_rate_limiter()
    result = await limiter.check_limit(
        rate_key, RATE_LIMIT_WINDOW_MS, RATE_LIMIT_MAX_REQUESTS
    )

    if not result.allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result.reset_at_ms // 1000)
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)

    # Add headers if it's a standard response
    if hasattr(response, 'headers'):
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at_ms // 1000)

    return response
