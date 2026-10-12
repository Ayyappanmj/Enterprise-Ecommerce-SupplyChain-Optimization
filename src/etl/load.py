"""
Loads a validated, transformed batch into data/processed/<table>.csv.

Incremental by construction: since extract() only ever returns rows newer
than the stored watermark, load() always appends (never overwrites), and the
first write for a table creates the file with headers.
"""
import os
from datetime import datetime, timezone

import pandas as pd

from .config import PROCESSED_DIR, REJECTED_DIR
from .exceptions import LoadError
from src.utils.logging_setup import get_logger

logger = get_logger("etl.load")


def load(df: pd.DataFrame, table_name: str) -> int:
    if df.empty:
        logger.info(f"[{table_name}] nothing new to load")
        return 0

    out_path = os.path.join(PROCESSED_DIR, f"{table_name}.csv")
    file_exists = os.path.exists(out_path)
    try:
        df.to_csv(out_path, mode="a", header=not file_exists, index=False)
    except Exception as exc:
        raise LoadError(f"Failed writing {out_path}: {exc}") from exc

    logger.info(f"[{table_name}] appended {len(df)} row(s) -> {out_path}")
    return len(df)


def quarantine(df: pd.DataFrame, table_name: str) -> int:
    if df is None or df.empty:
        return 0
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(REJECTED_DIR, f"{table_name}_rejected_{ts}.csv")
    df.to_csv(out_path, index=False)
    logger.warning(f"[{table_name}] quarantined {len(df)} row(s) -> {out_path}")
    return len(df)
