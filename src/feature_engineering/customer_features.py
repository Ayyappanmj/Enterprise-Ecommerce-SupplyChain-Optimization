"""
Customer Lifetime Value, Average Order Value, Repeat Purchase Rate.

CLV is provided two ways:
  - clv_historical_usd: actual revenue to date (sum of total_amount_usd) - no
    assumptions, just a fact about the data so far.
  - projected_clv_usd: a simple extrapolation (annualized order frequency x
    AOV x PROJECTED_CLV_HORIZON_YEARS) for customers with more than one
    order, so a frequency can actually be estimated. Single-order customers
    get NaN here rather than a frequency guessed from n=1.
"""
import numpy as np
import pandas as pd

from .config import PROJECTED_CLV_HORIZON_YEARS


def build(customers: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    agg = orders.groupby("customer_id").agg(
        num_orders=("order_id", "count"),
        clv_historical_usd=("total_amount_usd", "sum"),
        first_order_date=("order_date", "min"),
        last_order_date=("order_date", "max"),
    ).reset_index()

    agg["clv_historical_usd"] = agg["clv_historical_usd"].round(2)
    agg["avg_order_value_usd"] = np.round(agg["clv_historical_usd"] / agg["num_orders"], 2)
    agg["tenure_days"] = (agg["last_order_date"] - agg["first_order_date"]).dt.days
    agg["is_repeat_customer"] = agg["num_orders"] > 1

    tenure_years = agg["tenure_days"] / 365.0
    orders_per_year = np.where(tenure_years > 0, agg["num_orders"] / tenure_years, np.nan)
    agg["projected_clv_usd"] = np.where(
        agg["is_repeat_customer"],
        np.round(agg["avg_order_value_usd"] * orders_per_year * PROJECTED_CLV_HORIZON_YEARS, 2),
        np.nan,  # can't estimate a purchase frequency from a single order
    )

    df = customers.merge(agg, on="customer_id", how="left")
    df["num_orders"] = df["num_orders"].fillna(0).astype(int)
    df["is_repeat_customer"] = df["is_repeat_customer"].fillna(False)

    cols = ["customer_id", "country_id", "segment", "loyalty_tier", "signup_date",
            "num_orders", "clv_historical_usd", "avg_order_value_usd", "projected_clv_usd",
            "tenure_days", "is_repeat_customer", "first_order_date", "last_order_date"]
    return df[[c for c in cols if c in df.columns]]


def overall_repeat_purchase_rate(customer_features: pd.DataFrame) -> float:
    purchasers = customer_features[customer_features["num_orders"] > 0]
    if purchasers.empty:
        return 0.0
    return round(purchasers["is_repeat_customer"].mean(), 4)
