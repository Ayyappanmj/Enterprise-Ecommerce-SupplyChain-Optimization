"""
Validates a freshly extracted batch before it's allowed to reach data/processed/.

Each validate_* function returns (valid_df, rejected_df, issues) where
`issues` is a list of human-readable strings summarizing what was wrong.
Rows failing a check are quarantined (removed from valid_df) rather than
failing the whole batch, unless a REQUIRED column is missing entirely, in
which case a ValidationError is raised.
"""
import pandas as pd

from .exceptions import ValidationError
from src.utils.logging_setup import get_logger

logger = get_logger("etl.validators")


def _check_required_columns(df: pd.DataFrame, required: list, source_name: str):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValidationError(f"{source_name}: missing required columns {missing}")


def _quarantine(df: pd.DataFrame, mask_bad, reason: str, issues: list):
    """mask_bad: boolean Series, True = row is bad."""
    n_bad = int(mask_bad.sum())
    if n_bad:
        issues.append(f"{reason}: {n_bad} row(s)")
    bad_rows = df[mask_bad].copy()
    if n_bad:
        bad_rows["rejection_reason"] = reason
    return df[~mask_bad], bad_rows


def validate_web_orders(df: pd.DataFrame):
    issues, rejected_parts = [], []
    required = ["order_id", "customer_id", "order_date", "total_amount_usd", "order_status"]
    _check_required_columns(df, required, "web_orders")

    good = df.copy()

    dup_mask = good.duplicated(subset=["order_id"], keep="first")
    good, bad = _quarantine(good, dup_mask, "duplicate order_id", issues)
    rejected_parts.append(bad)

    null_mask = good["order_id"].isna() | good["customer_id"].isna() | good["order_date"].isna()
    good, bad = _quarantine(good, null_mask, "null primary/foreign key", issues)
    rejected_parts.append(bad)

    neg_mask = pd.to_numeric(good["total_amount_usd"], errors="coerce") < 0
    good, bad = _quarantine(good, neg_mask.fillna(False), "negative order total", issues)
    rejected_parts.append(bad)

    rejected = pd.concat(rejected_parts, ignore_index=True) if rejected_parts else pd.DataFrame()
    logger.info(f"validate_web_orders: {len(good)} valid, {len(rejected)} rejected. Issues: {issues}")
    return good, rejected, issues


def validate_inventory(df: pd.DataFrame):
    issues, rejected_parts = [], []
    required = ["inventory_id", "warehouse_id", "product_id", "stock_quantity"]
    _check_required_columns(df, required, "inventory_system")

    good = df.copy()

    dup_mask = good.duplicated(subset=["inventory_id"], keep="first")
    good, bad = _quarantine(good, dup_mask, "duplicate inventory_id", issues)
    rejected_parts.append(bad)

    neg_stock = pd.to_numeric(good["stock_quantity"], errors="coerce") < 0
    good, bad = _quarantine(good, neg_stock.fillna(False), "negative stock quantity", issues)
    rejected_parts.append(bad)

    null_mask = good["warehouse_id"].isna() | good["product_id"].isna()
    good, bad = _quarantine(good, null_mask, "null warehouse/product key", issues)
    rejected_parts.append(bad)

    rejected = pd.concat(rejected_parts, ignore_index=True) if rejected_parts else pd.DataFrame()
    logger.info(f"validate_inventory: {len(good)} valid, {len(rejected)} rejected. Issues: {issues}")
    return good, rejected, issues


def validate_shipping(df: pd.DataFrame):
    issues, rejected_parts = [], []
    required = ["shipping_id", "order_id", "ship_date", "shipping_status"]
    _check_required_columns(df, required, "shipping_api")

    good = df.copy()

    dup_mask = good.duplicated(subset=["shipping_id"], keep="first")
    good, bad = _quarantine(good, dup_mask, "duplicate shipping_id", issues)
    rejected_parts.append(bad)

    ship = pd.to_datetime(good["ship_date"], errors="coerce")
    deliv = pd.to_datetime(good.get("actual_delivery_date"), errors="coerce")
    impossible_mask = deliv.notna() & ship.notna() & (deliv < ship)
    good, bad = _quarantine(good, impossible_mask, "delivery date before ship date", issues)
    rejected_parts.append(bad)

    null_mask = good["order_id"].isna() | ship.isna() if "order_id" in good else pd.Series(False, index=good.index)
    good, bad = _quarantine(good, null_mask.reindex(good.index, fill_value=False), "null key/date", issues)
    rejected_parts.append(bad)

    rejected = pd.concat(rejected_parts, ignore_index=True) if rejected_parts else pd.DataFrame()
    logger.info(f"validate_shipping: {len(good)} valid, {len(rejected)} rejected. Issues: {issues}")
    return good, rejected, issues
