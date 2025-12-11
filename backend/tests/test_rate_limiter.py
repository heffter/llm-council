"""Tests for rate limiter backends."""

import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.rate_limiter import (
    RateLimitResult,
    MemoryRateLimiter,
    RedisRateLimiter,
    RateLimitBackend,
    get_rate_limiter,
    get_rate_limit_config,
)


# =============================================================================
# Test RateLimitResult
# =============================================================================

class TestRateLimitResult:
    """Tests for RateLimitResult dataclass."""

    def test_allowed_result(self):
        """Test result when request is allowed."""
        result = RateLimitResult(
            allowed=True,
            remaining=5,
            reset_at_ms=int(time.time() * 1000) + 60000
        )

        assert result.allowed is True
        assert result.remaining == 5
        assert result.retry_after_seconds is None

    def test_denied_result_calculates_retry_after(self):
        """Test retry_after is calculated when denied."""
        future_ms = int(time.time() * 1000) + 30000  # 30 seconds from now
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at_ms=future_ms
        )

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds >= 29  # Allow for timing variance


# =============================================================================
# Test MemoryRateLimiter
# =============================================================================

class TestMemoryRateLimiter:
    """Tests for in-memory rate limiter."""

    @pytest.fixture
    def limiter(self):
        """Create fresh limiter for each test."""
        return MemoryRateLimiter()

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, limiter):
        """Test first request is always allowed."""
        result = await limiter.check_limit("test_key", 60000, 10)

        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_increments_counter(self, limiter):
        """Test counter increments with each request."""
        for i in range(5):
            result = await limiter.check_limit("test_key", 60000, 10)
            assert result.remaining == 10 - (i + 1)

    @pytest.mark.asyncio
    async def test_exceeds_limit(self, limiter):
        """Test request is denied when limit exceeded."""
        # Use up all requests
        for _ in range(10):
            await limiter.check_limit("test_key", 60000, 10)

        # Next request should be denied
        result = await limiter.check_limit("test_key", 60000, 10)

        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter):
        """Test different keys have independent limits."""
        # Use up limit for key1
        for _ in range(10):
            await limiter.check_limit("key1", 60000, 10)

        # key2 should still have full quota
        result = await limiter.check_limit("key2", 60000, 10)

        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_window_reset(self, limiter):
        """Test counter resets after window expires."""
        # Use up all requests
        for _ in range(10):
            await limiter.check_limit("test_key", 100, 10)  # 100ms window

        # Wait for window to expire
        time.sleep(0.15)

        # Should be allowed again
        result = await limiter.check_limit("test_key", 100, 10)

        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_get_remaining_without_increment(self, limiter):
        """Test get_remaining doesn't increment counter."""
        await limiter.check_limit("test_key", 60000, 10)  # Use 1

        remaining = await limiter.get_remaining("test_key", 60000, 10)
        assert remaining == 9

        # Check again - should still be 9
        remaining = await limiter.get_remaining("test_key", 60000, 10)
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_get_remaining_unknown_key(self, limiter):
        """Test get_remaining returns max for unknown key."""
        remaining = await limiter.get_remaining("unknown_key", 60000, 10)
        assert remaining == 10

    @pytest.mark.asyncio
    async def test_health_check(self, limiter):
        """Test health check returns correct info."""
        health = await limiter.health_check()

        assert health["backend"] == "memory"
        assert health["status"] == "healthy"
        assert "keys_tracked" in health

    def test_backend_name(self, limiter):
        """Test backend name property."""
        assert limiter.backend_name == "memory"


# =============================================================================
# Test RedisRateLimiter
# =============================================================================

class TestRedisRateLimiter:
    """Tests for Redis-backed rate limiter."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_pipe = AsyncMock()
        mock_pipe.incr = MagicMock(return_value=mock_pipe)
        mock_pipe.pexpire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[1])  # First request
        mock_client.pipeline = MagicMock(return_value=mock_pipe)
        mock_client.get = AsyncMock(return_value="5")
        mock_client.info = AsyncMock(return_value={"connected_clients": 1})
        return mock_client

    @pytest.mark.asyncio
    async def test_check_limit_with_redis(self, mock_redis):
        """Test rate limiting with mocked Redis."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")

        with patch.object(limiter, '_get_client', return_value=mock_redis):
            result = await limiter.check_limit("test_key", 60000, 10)

        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_check_limit_fallback_on_error(self, mock_redis):
        """Test fallback to memory when Redis fails."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")

        # Make Redis fail
        mock_redis.pipeline.return_value.execute = AsyncMock(side_effect=Exception("Connection failed"))

        with patch.object(limiter, '_get_client', return_value=mock_redis):
            # Should fallback to memory limiter
            result = await limiter.check_limit("test_key", 60000, 10)

        assert result.allowed is True  # Memory fallback works

    @pytest.mark.asyncio
    async def test_check_limit_no_client_uses_fallback(self):
        """Test fallback when no Redis client available."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")

        with patch.object(limiter, '_get_client', return_value=None):
            result = await limiter.check_limit("test_key", 60000, 10)

        assert result.allowed is True  # Memory fallback works

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_redis):
        """Test health check when Redis is healthy."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")

        with patch.object(limiter, '_get_client', return_value=mock_redis):
            health = await limiter.health_check()

        assert health["backend"] == "redis"
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health check when Redis is unavailable."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")
        limiter._in_fallback_mode = True
        limiter._last_error = "Connection refused"

        with patch.object(limiter, '_get_client', return_value=None):
            health = await limiter.health_check()

        assert health["backend"] == "redis"
        assert health["status"] == "degraded"
        assert health["in_fallback_mode"] is True

    def test_backend_name_normal(self):
        """Test backend name when Redis is working."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")
        assert limiter.backend_name == "redis"

    def test_backend_name_fallback(self):
        """Test backend name when in fallback mode."""
        limiter = RedisRateLimiter("redis://localhost:6379/0")
        limiter._in_fallback_mode = True
        assert limiter.backend_name == "redis (fallback: memory)"


# =============================================================================
# Test Configuration
# =============================================================================

class TestRateLimitConfiguration:
    """Tests for rate limiter configuration."""

    def test_get_rate_limit_config(self):
        """Test config retrieval."""
        config = get_rate_limit_config()

        assert "backend" in config
        assert "redis_configured" in config

    def test_invalid_backend_raises_error(self):
        """Test invalid backend raises ValueError."""
        with patch.dict('os.environ', {'RATE_LIMIT_BACKEND': 'invalid'}):
            with pytest.raises(ValueError, match="Invalid RATE_LIMIT_BACKEND"):
                # Need to reload module to pick up new env var
                import importlib
                import backend.rate_limiter
                importlib.reload(backend.rate_limiter)

    def test_redis_backend_requires_url(self):
        """Test Redis backend requires REDIS_URL."""
        with patch.dict('os.environ', {'RATE_LIMIT_BACKEND': 'redis', 'REDIS_URL': ''}):
            with pytest.raises(ValueError, match="REDIS_URL is required"):
                import importlib
                import backend.rate_limiter
                importlib.reload(backend.rate_limiter)


# =============================================================================
# Test Middleware Integration (backwards compatibility)
# =============================================================================

class TestMiddlewareBackwardsCompatibility:
    """Ensure middleware still works with new rate limiter."""

    @pytest.mark.asyncio
    async def test_memory_limiter_parity(self):
        """Test MemoryRateLimiter matches old RateLimitStore behavior."""
        from backend.rate_limiter import MemoryRateLimiter

        limiter = MemoryRateLimiter()

        # Test same behavior as old implementation
        result1 = await limiter.check_limit("key", 60000, 5)
        assert result1.allowed is True
        assert result1.remaining == 4

        result2 = await limiter.check_limit("key", 60000, 5)
        assert result2.allowed is True
        assert result2.remaining == 3

        # Exhaust limit
        for _ in range(3):
            await limiter.check_limit("key", 60000, 5)

        result_blocked = await limiter.check_limit("key", 60000, 5)
        assert result_blocked.allowed is False
        assert result_blocked.remaining == 0
