"""
Generic, vectorized building blocks used by cleaning_engine.py. Every function
here operates on whole columns (no row-by-row python loops) so cleaning
scales to the full 500K-order dataset in seconds.
"""
import numpy as np
import pandas as pd

from .config import IQR_MULTIPLIER, COUNTRY_UTC_OFFSET_HOURS


def drop_duplicates(df: pd.DataFrame, subset: list) -> tuple:
    before = len(df)
    out = df.drop_duplicates(subset=subset, keep="first")
    return out, before - len(out)


def drop_null_critical(df: pd.DataFrame, critical_cols: list) -> tuple:
    if not critical_cols:
        return df, 0
    before = len(df)
    mask_ok = np.ones(len(df), dtype=bool)
    for c in critical_cols:
        if c in df.columns:
            mask_ok &= df[c].notna().values
    out = df[mask_ok]
    return out, before - len(out)


def fix_negative_values(df: pd.DataFrame, cols: list, clip_to_zero=True) -> tuple:
    """Flags (and by default clips to 0) negative values in columns that can
    never legitimately be negative, e.g. quantity, stock, price."""
    df = df.copy()
    n_fixed = 0
    for c in cols:
        if c not in df.columns:
            continue
        neg_mask = pd.to_numeric(df[c], errors="coerce") < 0
        n = int(neg_mask.sum())
        if n:
            n_fixed += n
            if clip_to_zero:
                df.loc[neg_mask, c] = 0
    return df, n_fixed


def flag_outliers_iqr(df: pd.DataFrame, cols: list) -> tuple:
    """Adds `<col>_is_outlier` boolean columns using Tukey's IQR fences.
    Outliers are FLAGGED, not deleted - shrinking margins caused by real
    high-value or heavily-discounted orders is exactly the signal this
    project's business questions care about, so silently dropping them would
    throw away the interesting rows."""
    df = df.copy()
    total_flagged = 0
    for c in cols:
        if c not in df.columns:
            continue
        series = pd.to_numeric(df[c], errors="coerce")
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr
        mask = (series < lower) | (series > upper)
        df[f"{c}_is_outlier"] = mask.fillna(False)
        total_flagged += int(mask.sum())
    return df, total_flagged


def fix_impossible_dates(df: pd.DataFrame, start_col: str, end_col: str) -> tuple:
    """Rows where end_col < start_col (e.g. delivered before shipped) are
    impossible. end_col is nulled out (kept as a "delivery not yet confirmed"
    row rather than deleting the whole shipment record)."""
    if start_col not in df.columns or end_col not in df.columns:
        return df, 0
    df = df.copy()
    start = pd.to_datetime(df[start_col], errors="coerce")
    end = pd.to_datetime(df[end_col], errors="coerce")
    bad_mask = end.notna() & start.notna() & (end < start)
    n_bad = int(bad_mask.sum())
    df.loc[bad_mask, end_col] = pd.NaT
    return df, n_bad


def normalize_to_utc(df: pd.DataFrame, date_cols: list, country_col: str,
                      countries_df: pd.DataFrame) -> pd.DataFrame:
    """Treats each timestamp as local time at `country_col`'s country and
    converts it to UTC by subtracting that country's standard-time offset.
    Adds `<col>_utc` columns alongside the originals (originals are kept for
    traceability)."""
    df = df.copy()
    country_name_map = countries_df.set_index("country_id")["country_name"]
    offsets = df[country_col].map(country_name_map).map(COUNTRY_UTC_OFFSET_HOURS).fillna(0)

    for c in date_cols:
        if c not in df.columns:
            continue
        ts = pd.to_datetime(df[c], errors="coerce")
        df[f"{c}_utc"] = ts - pd.to_timedelta(offsets, unit="h")
    return df


def convert_amount_to_local_currency(df: pd.DataFrame, usd_col: str, currency_col: str,
                                      date_col: str, fx_df: pd.DataFrame, out_col: str) -> pd.DataFrame:
    """Converts a USD amount to the order's local currency using the
    historical daily exchange rate closest to (on or before) the order date -
    a standard as-of join, done with merge_asof for speed instead of a
    row-by-row lookup."""
    df = df.copy()
    left = df[[date_col, currency_col]].copy()
    left["_row_order"] = np.arange(len(left))
    left[date_col] = pd.to_datetime(left[date_col], errors="coerce")
    left = left.sort_values(date_col)

    fx = fx_df.copy()
    fx["date"] = pd.to_datetime(fx["date"])

    merged_parts = []
    for currency, group in left.groupby(currency_col):
        fx_c = fx[fx["currency_code"] == currency].sort_values("date")
        if fx_c.empty:
            group = group.copy()
            group["rate_to_usd"] = np.nan
        else:
            group = pd.merge_asof(
                group, fx_c[["date", "rate_to_usd"]],
                left_on=date_col, right_on="date", direction="backward",
            )
        merged_parts.append(group)

    rates = pd.concat(merged_parts).sort_values("_row_order")["rate_to_usd"].values
    df[out_col] = np.round(pd.to_numeric(df[usd_col], errors="coerce") / rates, 2)
    return df
