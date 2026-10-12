"""
Source 3: Shipping API.

Pulls paginated shipping/tracking records from the mock Flask API
(shipping_api_server.py). The API deliberately fails ~8% of requests to
simulate a flaky third-party logistics provider, so every page fetch goes
through retry_with_backoff.
"""
import pandas as pd
import requests

from .config import (
    SHIPPING_API_BASE_URL, SHIPPING_API_PAGE_SIZE, SHIPPING_API_REQUEST_TIMEOUT,
    RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY,
)
from .exceptions import ExtractionError, TransientAPIError
from src.utils.logging_setup import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger("etl.extract.shipping_api")


@retry_with_backoff(
    max_attempts=RETRY_MAX_ATTEMPTS,
    base_delay=RETRY_BASE_DELAY,
    retry_on=(TransientAPIError, requests.ConnectionError, requests.Timeout),
)
def _fetch_page(since: str, page: int, page_size: int) -> dict:
    url = f"{SHIPPING_API_BASE_URL}/shipping"
    resp = requests.get(
        url, params={"since": since, "page": page, "page_size": page_size},
        timeout=SHIPPING_API_REQUEST_TIMEOUT,
    )
    if resp.status_code >= 500:
        raise TransientAPIError(f"Shipping API returned {resp.status_code} on page {page}")
    if resp.status_code != 200:
        # Non-5xx errors (4xx) are not retried - they indicate a client/request bug, not a transient fault.
        raise ExtractionError(f"Shipping API returned unexpected status {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def extract(watermark: str) -> pd.DataFrame:
    logger.info(f"Extracting Shipping API since {watermark}")
    try:
        first_page = _fetch_page(watermark, page=1, page_size=SHIPPING_API_PAGE_SIZE)
    except requests.exceptions.RequestException as exc:
        raise ExtractionError(
            f"Could not reach Shipping API at {SHIPPING_API_BASE_URL}. "
            f"Is `python -m src.etl.shipping_api_server` running? ({exc})"
        ) from exc

    total_pages = first_page["total_pages"]
    all_records = list(first_page["records"])
    logger.info(f"Shipping API: page 1/{total_pages} fetched ({first_page['total_records']} total records)")

    for page in range(2, total_pages + 1):
        data = _fetch_page(watermark, page=page, page_size=SHIPPING_API_PAGE_SIZE)
        all_records.extend(data["records"])
        logger.info(f"Shipping API: page {page}/{total_pages} fetched")

    df = pd.DataFrame(all_records)
    logger.info(f"Shipping API: {len(df)} record(s) extracted since {watermark}")
    return df


if __name__ == "__main__":
    print(extract("1970-01-01").head())
