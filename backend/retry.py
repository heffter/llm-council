"""Retry logic with exponential backoff for upstream calls."""

import asyncio
import random
from typing import TypeVar, Callable, Awaitable


T = TypeVar('T')


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    retries: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 10000
) -> T:
    """
    Execute an async function with exponential backoff retries.

    Args:
        fn: Async function to execute
        retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds (default: 1000)
        max_delay_ms: Maximum delay in milliseconds (default: 10000)

    Returns:
        Result from successful execution

    Raises:
        Exception: The last exception if all retries are exhausted
    """
    attempt = 0
    last_exception = None

    while attempt <= retries:
        try:
            return await fn()
        except Exception as e:
            last_exception = e
            attempt += 1

            # Don't retry on client errors (4xx)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if 400 <= e.response.status_code < 500:
                    raise

            # If we've exhausted retries, raise the exception
            if attempt > retries:
                raise

            # Calculate delay with exponential backoff and jitter
            delay_ms = min(
                base_delay_ms * (2 ** (attempt - 1)),
                max_delay_ms
            )
            # Add jitter: random between 50% and 100% of calculated delay
            jitter_factor = 0.5 + (random.random() * 0.5)
            actual_delay_ms = delay_ms * jitter_factor
            actual_delay_s = actual_delay_ms / 1000.0

            # Log retry attempt
            print(f"Retry attempt {attempt}/{retries} after {actual_delay_s:.2f}s: {e}")

            await asyncio.sleep(actual_delay_s)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise Exception("Retry logic failed unexpectedly")


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error should be retried, False otherwise
    """
    # Check for network/timeout errors
    error_str = str(error).lower()
    retryable_patterns = [
        'timeout',
        'connection',
        'network',
        'econnreset',
        'etimedout',
        '503',
        '502',
        '504',
        '500'
    ]

    return any(pattern in error_str for pattern in retryable_patterns)
