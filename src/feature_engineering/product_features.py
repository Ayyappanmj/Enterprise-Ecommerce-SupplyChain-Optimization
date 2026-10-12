"""
Product-level Gross Margin and Return Rate.

return_rate here = (number of line items with at least one return record) /
(number of line items sold) for that product - i.e. "what share of sold units
came back", the standard operational definition, computed at the order_item
grain since that's what `returns` references (not raw quantity, since the
dataset models a return as one event per order line, not partial-quantity
returns).
"""
import numpy as np
import pandas as pd


def build(products: pd.DataFrame, order_items: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    items = order_items.merge(products[["product_id", "unit_cost_usd", "category", "sub_category"]],
                               on="product_id", how="left")
    items["line_cost_usd"] = items["quantity"] * items["unit_cost_usd"]

    agg = items.groupby("product_id").agg(
        units_sold=("quantity", "sum"),
        line_items_sold=("order_item_id", "count"),
        revenue_usd=("line_total_usd", "sum"),
        cost_usd=("line_cost_usd", "sum"),
    ).reset_index()

    agg["gross_profit_usd"] = np.round(agg["revenue_usd"] - agg["cost_usd"], 2)
    agg["gross_margin_pct"] = np.where(
        agg["revenue_usd"] > 0, np.round(agg["gross_profit_usd"] / agg["revenue_usd"], 4), np.nan
    )

    returned_items = returns.merge(order_items[["order_item_id", "product_id"]], on="order_item_id", how="left")
    returns_by_product = returned_items.groupby("product_id").size().rename("line_items_returned")
    agg = agg.merge(returns_by_product, on="product_id", how="left")
    agg["line_items_returned"] = agg["line_items_returned"].fillna(0).astype(int)
    agg["return_rate"] = np.where(
        agg["line_items_sold"] > 0, np.round(agg["line_items_returned"] / agg["line_items_sold"], 4), np.nan
    )

    df = products.merge(agg, on="product_id", how="left")
    for c in ["units_sold", "line_items_sold", "line_items_returned"]:
        df[c] = df[c].fillna(0).astype(int)

    cols = ["product_id", "product_name", "category", "sub_category", "supplier_id",
            "unit_cost_usd", "unit_price_usd", "units_sold", "revenue_usd", "gross_profit_usd",
            "gross_margin_pct", "line_items_sold", "line_items_returned", "return_rate"]
    return df[[c for c in cols if c in df.columns]]
