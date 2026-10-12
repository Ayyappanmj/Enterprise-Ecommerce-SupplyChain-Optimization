"""
Source 1: Web Orders CSV.

Simulates pulling the day's new/updated orders out of the e-commerce
platform's order export. Incremental: only rows with order_date strictly
after the stored watermark are returned.
"""
import os

import pandas as pd

from .config import RAW_DIR
from .exceptions import ExtractionError
from src.utils.logging_setup import get_logger

logger = get_logger("etl.extract.web_orders")

ORDERS_CSV = os.path.join(RAW_DIR, "orders.csv")


def extract(watermark: str) -> pd.DataFrame:
    if not os.path.exists(ORDERS_CSV):
        raise ExtractionError(f"Web Orders source file not found: {ORDERS_CSV}")

    logger.info(f"Extracting Web Orders CSV since {watermark}")
    try:
        df = pd.read_csv(ORDERS_CSV, parse_dates=["order_date"])
    except Exception as exc:
        raise ExtractionError(f"Failed to read {ORDERS_CSV}: {exc}") from exc

    wm_ts = pd.to_datetime(watermark)
    new_rows = df[df["order_date"] > wm_ts].copy()
    logger.info(f"Web Orders: {len(new_rows)} new/changed row(s) since {watermark} (of {len(df)} total)")
    return new_rows


if __name__ == "__main__":
    print(extract("1970-01-01").head())
