"""Brain CLI v2 — Exponential backoff retry for API calls."""

from __future__ import annotations

import sys
import time

from .errors import APIError, RetryableError

# Retry on these HTTP status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Do NOT retry on these
NON_RETRYABLE_CODES = {400, 401, 403, 404}

MAX_RETRIES = 3  # Total attempts = MAX_RETRIES + 1
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 8.0  # seconds


def is_retryable(status_code: int | None) -> bool:
    """Check if an HTTP status code is retryable."""
    if status_code is None:
        return False
    return status_code in RETRYABLE_STATUS_CODES


def calculate_delay(attempt: int) -> float:
    """Calculate exponential backoff delay.

    attempt is 0-indexed.
    """
    delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
    return delay


def log_retry(attempt: int, max_attempts: int, status_code: int | None, delay: float) -> None:
    """Log retry attempt to stderr."""
    code_str = f" (HTTP {status_code})" if status_code else ""
    print(
        f"Retrying (attempt {attempt}/{max_attempts}){code_str} after {delay:.1f}s...",
        file=sys.stderr,
    )


def retry_with_backoff(func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """Call func with exponential backoff on retryable errors.

    func should raise RetryableError on transient failures.
    Returns the result of func on success.
    Raises APIError after all retries exhausted.
    """

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except RetryableError as e:
            if attempt < max_retries:
                delay = calculate_delay(attempt)
                log_retry(attempt + 1, max_retries + 1, e.status_code, delay)
                time.sleep(delay)
            else:
                # All retries exhausted
                raise APIError(
                    f"API call failed after {max_retries + 1} attempts: {e}",
                    status_code=e.status_code,
                ) from e
