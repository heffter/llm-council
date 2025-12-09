"""Unit tests for middleware module."""

import pytest
import time
from unittest.mock import Mock, AsyncMock
from backend.middleware import (
    RateLimitStore,
    shared_secret_middleware,
    rate_limit_middleware
)


class TestRateLimitStore:
    """Tests for RateLimitStore class."""

    def test_first_request_allowed(self):
        """First request should be allowed."""
        store = RateLimitStore()
        allowed, remaining, reset_at = store.check_and_increment(
            "test_key", window_ms=60000, max_requests=10
        )

        assert allowed is True
        assert remaining == 9
        assert reset_at > int(time.time() * 1000)

    def test_increments_counter(self):
        """Counter should increment with each request."""
        store = RateLimitStore()

        # First request
        _, remaining1, _ = store.check_and_increment("test_key", 60000, 10)
        assert remaining1 == 9

        # Second request
        _, remaining2, _ = store.check_and_increment("test_key", 60000, 10)
        assert remaining2 == 8

    def test_exceeds_limit(self):
        """Requests exceeding limit should be denied."""
        store = RateLimitStore()
        max_requests = 3

        # Use up the limit
        for i in range(max_requests):
            allowed, _, _ = store.check_and_increment("test_key", 60000, max_requests)
            assert allowed is True

        # Next request should be denied
        allowed, remaining, _ = store.check_and_increment("test_key", 60000, max_requests)
        assert allowed is False
        assert remaining == 0

    def test_window_reset(self):
        """Counter should reset after window expires."""
        store = RateLimitStore()
        window_ms = 100  # Short window for testing
        max_requests = 2

        # Use up limit
        store.check_and_increment("test_key", window_ms, max_requests)
        store.check_and_increment("test_key", window_ms, max_requests)

        # Should be blocked
        allowed, _, _ = store.check_and_increment("test_key", window_ms, max_requests)
        assert allowed is False

        # Wait for window to expire
        time.sleep(0.15)

        # Should be allowed again
        allowed, remaining, _ = store.check_and_increment("test_key", window_ms, max_requests)
        assert allowed is True
        assert remaining == max_requests - 1

    def test_different_keys_independent(self):
        """Different keys should have independent counters."""
        store = RateLimitStore()
        max_requests = 2

        # Use up limit for key1
        store.check_and_increment("key1", 60000, max_requests)
        store.check_and_increment("key1", 60000, max_requests)
        allowed1, _, _ = store.check_and_increment("key1", 60000, max_requests)
        assert allowed1 is False

        # key2 should still have full quota
        allowed2, remaining2, _ = store.check_and_increment("key2", 60000, max_requests)
        assert allowed2 is True
        assert remaining2 == max_requests - 1

    def test_reset_at_timing(self):
        """reset_at should be approximately window_ms in the future."""
        store = RateLimitStore()
        window_ms = 60000

        now_ms = int(time.time() * 1000)
        _, _, reset_at = store.check_and_increment("test_key", window_ms, 10)

        # Should be approximately window_ms in the future (allow 100ms tolerance)
        expected_reset = now_ms + window_ms
        assert abs(reset_at - expected_reset) < 100


class TestSharedSecretMiddleware:
    """Tests for shared_secret_middleware function."""

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request."""
        request = Mock()
        request.method = "POST"
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Mock call_next function."""
        return AsyncMock(return_value=Mock(status_code=200))

    @pytest.mark.asyncio
    async def test_no_token_configured_passes_through(
        self, mock_request, mock_call_next, monkeypatch
    ):
        """When SHARED_WRITE_TOKEN not set, all requests pass through."""
        monkeypatch.delenv("SHARED_WRITE_TOKEN", raising=False)

        # Reload middleware to pick up env change
        from backend.middleware import shared_secret_middleware

        response = await shared_secret_middleware(mock_request, mock_call_next)

        assert mock_call_next.called
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_request_passes_without_token(
        self, mock_call_next, monkeypatch
    ):
        """GET requests should pass through even with token configured."""
        monkeypatch.setenv("SHARED_WRITE_TOKEN", "test-secret")

        # Reload to pick up env
        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.method = "GET"
        request.headers = {}

        response = await middleware.shared_secret_middleware(request, mock_call_next)
        assert mock_call_next.called

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, monkeypatch):
        """POST request without token should return 401."""
        monkeypatch.setenv("SHARED_WRITE_TOKEN", "test-secret")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.method = "POST"
        request.headers = {}

        call_next = AsyncMock()
        response = await middleware.shared_secret_middleware(request, call_next)

        assert not call_next.called
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self, monkeypatch):
        """POST request with wrong token should return 401."""
        monkeypatch.setenv("SHARED_WRITE_TOKEN", "correct-secret")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.method = "POST"

        def get_header(name):
            return "wrong-secret" if name == "X-Shared-Token" else None

        request.headers = Mock()
        request.headers.get = get_header

        call_next = AsyncMock()
        response = await middleware.shared_secret_middleware(request, call_next)

        assert not call_next.called
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_token_passes(self, mock_call_next, monkeypatch):
        """POST request with correct token should pass through."""
        monkeypatch.setenv("SHARED_WRITE_TOKEN", "correct-secret")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.method = "POST"

        def get_header(name):
            return "correct-secret" if name == "X-Shared-Token" else None

        request.headers = Mock()
        request.headers.get = get_header

        response = await middleware.shared_secret_middleware(request, mock_call_next)

        assert mock_call_next.called
        assert response.status_code == 200


class TestRateLimitMiddleware:
    """Tests for rate_limit_middleware function."""

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request."""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = Mock()
        request.headers.get = lambda x: None
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Mock call_next function."""
        return AsyncMock(return_value=Mock(status_code=200, headers={}))

    @pytest.mark.asyncio
    async def test_disabled_by_default_passes_through(
        self, mock_request, mock_call_next, monkeypatch
    ):
        """Rate limiting disabled by default."""
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)

        from importlib import reload
        from backend import middleware
        reload(middleware)

        response = await middleware.rate_limit_middleware(mock_request, mock_call_next)
        assert mock_call_next.called

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, mock_call_next, monkeypatch):
        """Requests under limit should be allowed."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "5")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_MS", "60000")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = Mock()
        request.headers.get = lambda x: None

        # Make 3 requests (under limit of 5)
        for _ in range(3):
            response = await middleware.rate_limit_middleware(request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, monkeypatch):
        """Requests over limit should return 429."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")
        monkeypatch.setenv("RATE_LIMIT_WINDOW_MS", "60000")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.2"  # Different IP to avoid conflicts
        request.headers = Mock()
        request.headers.get = lambda x: None

        call_next = AsyncMock(return_value=Mock(status_code=200, headers={}))

        # Use up limit
        await middleware.rate_limit_middleware(request, call_next)
        await middleware.rate_limit_middleware(request, call_next)

        # Next request should be blocked
        response = await middleware.rate_limit_middleware(request, call_next)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_sets_rate_limit_headers(self, monkeypatch):
        """Should set X-RateLimit-Remaining header."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "10")

        from importlib import reload
        from backend import middleware
        reload(middleware)

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.3"
        request.headers = Mock()
        request.headers.get = lambda x: None

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.rate_limit_middleware(request, call_next)

        # Check that X-RateLimit-Remaining was set
        assert "X-RateLimit-Remaining" in response.headers
        assert int(response.headers["X-RateLimit-Remaining"]) == 9
