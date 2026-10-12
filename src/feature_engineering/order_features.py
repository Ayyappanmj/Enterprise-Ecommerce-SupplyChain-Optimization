"""
Order-level feature engineering: Gross Margin, Net Margin (and the profit
figures they're built from). Everything here is vectorized pandas/NumPy -
groupby + merge + array arithmetic, no per-row Python loops - so it scales to
500K orders / 1.5M order lines in well under a second.

Definitions (see config.py for the one assumption involved):
    product_revenue_usd = subtotal_usd * (1 - discount_pct)      # order-level discount applied
    cogs_usd            = sum(quantity * unit_cost_usd) over the order's line items
    gross_profit_usd    = product_revenue_usd - cogs_usd
    gross_margin_pct    = gross_profit_usd / product_revenue_usd

    net_profit_usd       = gross_profit_usd - shipping_cost_usd - refund_amount_usd - opex_usd
    opex_usd             = product_revenue_usd * ASSUMED_OPEX_RATE   (documented assumption)
    net_margin_pct        = net_profit_usd / product_revenue_usd

Tax is deliberately excluded from revenue: it's collected on behalf of a tax
authority and remitted, not company revenue, so including it would overstate
margin.
"""
import numpy as np
import pandas as pd

from .config import ASSUMED_OPEX_RATE


def build(orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame,
          returns: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()

    # --- COGS: join line items to product cost, sum per order ---
    items_cost = order_items.merge(
        products[["product_id", "unit_cost_usd"]], on="product_id", how="left"
    )
    items_cost["line_cost_usd"] = items_cost["quantity"] * items_cost["unit_cost_usd"]
    cogs_by_order = items_cost.groupby("order_id")["line_cost_usd"].sum().rename("cogs_usd")
    df = df.merge(cogs_by_order, on="order_id", how="left")
    # .astype(float) guards against a real dtype-contamination bug: if
    # order_items/returns is empty, groupby().sum() on an empty frame returns
    # object dtype, and fillna(0.0) does NOT upcast it back to float64 - the
    # column silently stays object-dtype with Python floats inside. Later
    # arithmetic on an object-dtype column falls back to pure-Python elementwise
    # ops, where 0.0/0.0 raises ZeroDivisionError instead of returning NaN/inf
    # the way numpy float64 division does. Caught by test_zero_revenue_order_
    # does_not_divide_by_zero in tests/test_feature_engineering.py.
    df["cogs_usd"] = df["cogs_usd"].fillna(0.0).astype(float)

    # --- Refunds attributable to each order ---
    refunds_by_order = returns.groupby("order_id")["refund_amount_usd"].sum().rename("refund_amount_usd")
    df = df.merge(refunds_by_order, on="order_id", how="left")
    df["refund_amount_usd"] = df["refund_amount_usd"].fillna(0.0).astype(float)  # see note above
    returned_order_ids = set(returns["order_id"].unique())
    df["is_returned"] = df["order_id"].isin(returned_order_ids)

    # --- Revenue, gross margin ---
    df["product_revenue_usd"] = np.round(df["subtotal_usd"] * (1 - df["discount_pct"]), 2)
    df["gross_profit_usd"] = np.round(df["product_revenue_usd"] - df["cogs_usd"], 2)
    df["gross_margin_pct"] = np.where(
        df["product_revenue_usd"] > 0,
        np.round(df["gross_profit_usd"] / df["product_revenue_usd"], 4),
        np.nan,
    )

    # --- Net margin ---
    df["opex_usd"] = np.round(df["product_revenue_usd"] * ASSUMED_OPEX_RATE, 2)
    df["net_profit_usd"] = np.round(
        df["gross_profit_usd"] - df["shipping_cost_usd"] - df["refund_amount_usd"] - df["opex_usd"], 2
    )
    df["net_margin_pct"] = np.where(
        df["product_revenue_usd"] > 0,
        np.round(df["net_profit_usd"] / df["product_revenue_usd"], 4),
        np.nan,
    )

    cols = [
        "order_id", "customer_id", "warehouse_id", "ship_country_id", "order_date",
        "order_status", "currency_code", "product_revenue_usd", "cogs_usd", "gross_profit_usd",
        "gross_margin_pct", "shipping_cost_usd", "tax_amount_usd", "refund_amount_usd",
        "opex_usd", "net_profit_usd", "net_margin_pct", "is_returned",
    ]
    return df[[c for c in cols if c in df.columns]]
