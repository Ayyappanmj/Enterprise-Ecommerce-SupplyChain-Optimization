import os

import pandas as pd

from .config import CLEANED_DIR

DATE_COLS_BY_TABLE = {
    "orders": ["order_date", "order_date_utc"],
    "customers": ["signup_date", "birth_date"],
    "products": ["launch_date"],
    "shipping": ["ship_date", "promised_delivery_date", "actual_delivery_date"],
    "returns": ["return_date"],
    "payments": ["payment_date"],
    "inventory": ["last_restock_date"],
}


def load(table_name: str) -> pd.DataFrame:
    path = os.path.join(CLEANED_DIR, f"{table_name}_clean.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.cleaning.run_cleaning` first (Phase 4)."
        )
    parse_dates = DATE_COLS_BY_TABLE.get(table_name, [])
    return pd.read_csv(path, parse_dates=[c for c in parse_dates])
