"""
Minimal standardization applied to every source right before load: consistent
column typing plus ingestion metadata. Business-logic transforms (margins,
CLV, delay buckets, etc.) belong to Phase 5 (feature engineering), not here -
Phase 2's job is just to get clean, structurally-sound data staged reliably.
"""
from datetime import datetime, timezone

import pandas as pd


def add_ingestion_metadata(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    df = df.copy()
    df["_source_system"] = source_name
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    return df


def standardize_dates(df: pd.DataFrame, date_columns: list) -> pd.DataFrame:
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
