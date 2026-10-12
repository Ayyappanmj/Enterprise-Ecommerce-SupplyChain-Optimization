"""
Profit by Country: rolls up order_features (already carrying revenue, COGS,
shipping cost, refunds, profit) by ship_country_id, and adds each country's
average delivery delay by joining through shipping -> orders.
"""
import numpy as np
import pandas as pd


def build(order_features: pd.DataFrame, countries: pd.DataFrame, regions: pd.DataFrame,
          shipping: pd.DataFrame) -> pd.DataFrame:
    agg = order_features.groupby("ship_country_id").agg(
        num_orders=("order_id", "count"),
        num_returned_orders=("is_returned", "sum"),
        product_revenue_usd=("product_revenue_usd", "sum"),
        cogs_usd=("cogs_usd", "sum"),
        gross_profit_usd=("gross_profit_usd", "sum"),
        shipping_cost_usd=("shipping_cost_usd", "sum"),
        refund_amount_usd=("refund_amount_usd", "sum"),
        net_profit_usd=("net_profit_usd", "sum"),
    ).reset_index()

    agg["gross_margin_pct"] = np.round(agg["gross_profit_usd"] / agg["product_revenue_usd"], 4)
    agg["net_margin_pct"] = np.round(agg["net_profit_usd"] / agg["product_revenue_usd"], 4)
    agg["return_rate"] = np.round(agg["num_returned_orders"] / agg["num_orders"], 4)

    delay_by_country = (
        shipping.merge(order_features[["order_id", "ship_country_id"]], on="order_id", how="inner")
        .groupby("ship_country_id")["delivery_delay_days"].mean().round(2)
        .rename("avg_delivery_delay_days")
    )
    agg = agg.merge(delay_by_country, on="ship_country_id", how="left")

    df = countries.merge(agg, left_on="country_id", right_on="ship_country_id", how="left")
    df = df.merge(regions[["region_id", "region_name"]], on="region_id", how="left")

    cols = ["country_id", "country_name", "region_id", "region_name", "num_orders",
            "product_revenue_usd", "cogs_usd", "gross_profit_usd", "gross_margin_pct",
            "shipping_cost_usd", "refund_amount_usd", "net_profit_usd", "net_margin_pct",
            "return_rate", "avg_delivery_delay_days"]
    return df[[c for c in cols if c in df.columns]].sort_values("net_profit_usd", ascending=False)
