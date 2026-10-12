"""Retry decorator with exponential backoff + jitter, for flaky external calls
(e.g. the mock Shipping API, which deliberately fails ~8% of requests)."""
import functools
import random
import time

from .logging_setup import get_logger

logger = get_logger("etl.retry")


def retry_with_backoff(max_attempts=5, base_delay=0.5, max_delay=8.0, retry_on=(Exception,)):
    """Retries the wrapped function up to `max_attempts` times, sleeping
    base_delay * 2**attempt seconds (capped at max_delay) between attempts,
    with +/-25% jitter so repeated failures don't retry in lockstep."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed permanently after {attempt} attempts: {exc}"
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay *= random.uniform(0.75, 1.25)
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed ({exc}); "
                        f"retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
        return wrapper
    return decorator
