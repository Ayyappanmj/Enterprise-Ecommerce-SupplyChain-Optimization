"""Phase 1: Returns, Payments, Marketing_Campaigns."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED, ORDER_DATE_START, ORDER_DATE_END
from .utils import zero_pad_id, random_dates


def generate_returns(df_orders, df_order_items):
    rng = np.random.default_rng(SEED + 15)
    n = CFG["n_returns"]

    items = df_order_items.merge(
        df_orders[["order_id", "order_date"]], on="order_id", how="inner"
    ).sample(n, replace=True, random_state=SEED + 15).reset_index(drop=True)

    return_date = pd.to_datetime(items["order_date"]) + pd.to_timedelta(rng.integers(2, 30, size=n), unit="D")
    status = rng.choice(ref.RETURN_STATUSES, size=n, p=[0.15, 0.25, 0.10, 0.40, 0.10])
    refund_amount = np.where(
        np.isin(status, ["Refunded"]), items["line_total_usd"].values,
        np.where(np.isin(status, ["Approved", "Received"]), items["line_total_usd"].values * 0.5, 0.0),
    )

    df = pd.DataFrame({
        "return_id": zero_pad_id("RET", range(1, n + 1), 7),
        "order_id": items["order_id"].values,
        "order_item_id": items["order_item_id"].values,
        "return_date": return_date,
        "return_reason": rng.choice(ref.RETURN_REASONS, size=n),
        "return_status": status,
        "refund_amount_usd": np.round(refund_amount, 2),
        "condition": rng.choice(ref.RETURN_CONDITIONS, size=n),
    })
    df.to_csv(os.path.join(RAW_DIR, "returns.csv"), index=False)
    print(f"returns: {len(df)}")
    return df


def generate_payments(df_orders):
    rng = np.random.default_rng(SEED + 16)
    n = len(df_orders)

    payment_date = pd.to_datetime(df_orders["order_date"]) + pd.to_timedelta(rng.integers(0, 2, size=n), unit="D")
    status = np.where(
        df_orders["order_status"].values == "Cancelled",
        rng.choice(["Failed", "Refunded"], size=n),
        rng.choice(ref.PAYMENT_STATUSES[:1] + ["Pending"], size=n, p=[0.95, 0.05]),
    )

    df = pd.DataFrame({
        "payment_id": zero_pad_id("PAY", range(1, n + 1), 8),
        "order_id": df_orders["order_id"].values,
        "payment_method": df_orders["payment_method"].values,
        "payment_date": payment_date,
        "amount_usd": df_orders["total_amount_usd"].values,
        "payment_status": status,
        "transaction_currency": df_orders["currency_code"].values,
    })
    df.to_csv(os.path.join(RAW_DIR, "payments.csv"), index=False)
    print(f"payments: {len(df)}")
    return df


def generate_marketing_campaigns(df_regions, df_countries):
    rng = np.random.default_rng(SEED + 17)
    n = CFG["n_campaigns"]

    starts = random_dates(rng, ORDER_DATE_START, ORDER_DATE_END, n)
    durations = rng.integers(7, 60, size=n)
    ends = starts + pd.to_timedelta(durations, unit="D")
    regions = df_regions.sample(n, replace=True, random_state=SEED + 17).reset_index(drop=True)
    countries = df_countries[df_countries["region_id"].isin(regions["region_id"])]

    target_country = []
    for rid in regions["region_id"]:
        pool = df_countries[df_countries["region_id"] == rid]["country_id"].values
        target_country.append(rng.choice(pool) if len(pool) else None)

    df = pd.DataFrame({
        "campaign_id": zero_pad_id("CMP", range(1, n + 1), 5),
        "campaign_name": [f"{rng.choice(ref.MARKETING_CHANNELS)} Push {i}" for i in range(n)],
        "channel": rng.choice(ref.MARKETING_CHANNELS, size=n),
        "start_date": starts.date,
        "end_date": ends.date,
        "budget_usd": np.round(rng.gamma(shape=2.0, scale=5000, size=n) + 500, 2),
        "target_region_id": regions["region_id"].values,
        "target_country_id": target_country,
    })
    df.to_csv(os.path.join(RAW_DIR, "marketing_campaigns.csv"), index=False)
    print(f"marketing_campaigns: {len(df)}")
    return df


if __name__ == "__main__":
    print("Run via run_all.py so upstream tables (orders/order_items/regions/countries) are available.")
