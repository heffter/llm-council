"""Unit tests for retry module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from backend.retry import with_retries


class TestWithRetries:
    """Tests for with_retries function."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Function succeeding on first try should not retry."""
        mock_fn = AsyncMock(return_value="success")

        result = await with_retries(mock_fn, retries=3)

        assert result == "success"
        assert mock_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Function should retry on transient failures."""
        mock_fn = AsyncMock(side_effect=[
            Exception("Transient error"),
            Exception("Transient error"),
            "success"
        ])

        result = await with_retries(mock_fn, retries=3)

        assert result == "success"
        assert mock_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Should raise exception after exhausting retries."""
        mock_fn = AsyncMock(side_effect=Exception("Persistent error"))

        with pytest.raises(Exception, match="Persistent error"):
            await with_retries(mock_fn, retries=2)

        assert mock_fn.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_errors(self):
        """Should not retry on 4xx HTTP errors."""
        # Mock an error with response.status_code attribute
        error = Exception("Client error")
        error.response = Mock()
        error.response.status_code = 400

        mock_fn = AsyncMock(side_effect=error)

        with pytest.raises(Exception, match="Client error"):
            await with_retries(mock_fn, retries=3)

        # Should only try once, no retries
        assert mock_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_5xx_errors(self):
        """Should retry on 5xx HTTP errors."""
        error = Exception("Server error")
        error.response = Mock()
        error.response.status_code = 500

        mock_fn = AsyncMock(side_effect=[error, error, "success"])

        result = await with_retries(mock_fn, retries=3)

        assert result == "success"
        assert mock_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Delays between retries should increase exponentially."""
        call_times = []

        async def failing_fn():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise Exception("Retry me")
            return "success"

        await with_retries(
            failing_fn,
            retries=3,
            base_delay_ms=100,  # 100ms base delay
            max_delay_ms=10000
        )

        # Calculate delays between calls
        delays = [
            (call_times[i] - call_times[i-1]) * 1000  # Convert to ms
            for i in range(1, len(call_times))
        ]

        # First delay should be around 100ms (with jitter)
        assert 50 <= delays[0] <= 150

        # Second delay should be around 200ms (2^1 * 100ms with jitter)
        assert 100 <= delays[1] <= 300

    @pytest.mark.asyncio
    async def test_max_delay_capped(self):
        """Delay should be capped at max_delay_ms."""
        call_times = []

        async def failing_fn():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise Exception("Retry me")
            return "success"

        await with_retries(
            failing_fn,
            retries=5,
            base_delay_ms=1000,
            max_delay_ms=500  # Max delay smaller than potential exponential value
        )

        # All delays should be capped at max_delay_ms with jitter
        delays = [
            (call_times[i] - call_times[i-1]) * 1000
            for i in range(1, len(call_times))
        ]

        for delay in delays:
            # With jitter factor (0.5-1.0), max observed delay is max_delay_ms * 1.0
            assert delay <= 600  # 500 * 1.2 for some tolerance

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Jitter should add randomness to delays."""
        delays = []

        for _ in range(5):
            call_times = []

            async def failing_fn():
                call_times.append(asyncio.get_event_loop().time())
                if len(call_times) < 2:
                    raise Exception("Retry me")
                return "success"

            await with_retries(failing_fn, retries=2, base_delay_ms=100)

            if len(call_times) >= 2:
                delay = (call_times[1] - call_times[0]) * 1000
                delays.append(delay)

        # Delays should not all be identical due to jitter
        assert len(set(delays)) > 1, "Expected variation in delays due to jitter"

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """With zero retries, should only try once."""
        mock_fn = AsyncMock(side_effect=Exception("Error"))

        with pytest.raises(Exception, match="Error"):
            await with_retries(mock_fn, retries=0)

        assert mock_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_custom_base_delay(self):
        """Should respect custom base_delay_ms parameter."""
        call_times = []

        async def failing_fn():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 2:
                raise Exception("Retry me")
            return "success"

        await with_retries(
            failing_fn,
            retries=2,
            base_delay_ms=200  # Custom base delay
        )

        delay_ms = (call_times[1] - call_times[0]) * 1000

        # With jitter (0.5-1.0 factor), expect 100-200ms delay
        assert 100 <= delay_ms <= 300
