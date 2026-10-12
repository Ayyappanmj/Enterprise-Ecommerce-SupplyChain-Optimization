"""
Source 2: Inventory System CSV.

Simulates a nightly export from the warehouse inventory system. Incremental:
only rows whose last_restock_date is strictly after the stored watermark are
treated as "changed since last run" (a reasonable proxy for a system that
doesn't expose a dedicated updated_at column).
"""
import os

import pandas as pd

from .config import RAW_DIR
from .exceptions import ExtractionError
from src.utils.logging_setup import get_logger

logger = get_logger("etl.extract.inventory")

INVENTORY_CSV = os.path.join(RAW_DIR, "inventory.csv")


def extract(watermark: str) -> pd.DataFrame:
    if not os.path.exists(INVENTORY_CSV):
        raise ExtractionError(f"Inventory source file not found: {INVENTORY_CSV}")

    logger.info(f"Extracting Inventory System CSV since {watermark}")
    try:
        df = pd.read_csv(INVENTORY_CSV, parse_dates=["last_restock_date"])
    except Exception as exc:
        raise ExtractionError(f"Failed to read {INVENTORY_CSV}: {exc}") from exc

    wm_ts = pd.to_datetime(watermark)
    new_rows = df[df["last_restock_date"] > wm_ts].copy()
    logger.info(f"Inventory: {len(new_rows)} new/changed row(s) since {watermark} (of {len(df)} total)")
    return new_rows


if __name__ == "__main__":
    print(extract("1970-01-01").head())
