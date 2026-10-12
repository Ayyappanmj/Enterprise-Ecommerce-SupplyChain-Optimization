"""
Shipping Delay (shipment-level) and Warehouse Utilization (warehouse-level).
"""
import numpy as np
import pandas as pd

from .config import DELAY_THRESHOLD_DAYS


def build_shipping_delay_features(shipping: pd.DataFrame) -> pd.DataFrame:
    df = shipping.copy()
    df["is_delayed"] = df["delivery_delay_days"] > DELAY_THRESHOLD_DAYS

    bins = [-np.inf, 0, DELAY_THRESHOLD_DAYS, 7, 14, np.inf]
    labels = ["Early/On-time", f"Minor (1-{DELAY_THRESHOLD_DAYS}d)", "Moderate (4-7d)",
              "Major (8-14d)", "Severe (15d+)"]
    df["delay_bucket"] = pd.cut(df["delivery_delay_days"], bins=bins, labels=labels)

    cols = ["shipping_id", "order_id", "route_id", "partner_id", "ship_date",
            "delivery_delay_days", "is_delayed", "delay_bucket", "shipping_status"]
    return df[[c for c in cols if c in df.columns]]


def build_warehouse_utilization(inventory: pd.DataFrame, warehouses: pd.DataFrame,
                                 orders: pd.DataFrame, shipping: pd.DataFrame,
                                 shipping_routes: pd.DataFrame) -> pd.DataFrame:
    stock_by_wh = inventory.groupby("warehouse_id")["stock_quantity"].sum().rename("total_stock_units")

    df = warehouses.merge(stock_by_wh, on="warehouse_id", how="left")
    # .astype(float): same empty-groupby dtype-contamination guard as
    # order_features.py - if inventory is ever empty, fillna(0) alone would
    # leave this column as object dtype and later division could raise
    # ZeroDivisionError instead of producing NaN/inf.
    df["total_stock_units"] = df["total_stock_units"].fillna(0).astype(float)
    df["utilization_pct"] = np.round(
        np.where(df["capacity_units"] > 0, df["total_stock_units"] / df["capacity_units"] * 100, np.nan), 2
    )

    orders_by_wh = orders.groupby("warehouse_id").size().rename("orders_fulfilled")
    df = df.merge(orders_by_wh, on="warehouse_id", how="left")
    df["orders_fulfilled"] = df["orders_fulfilled"].fillna(0).astype(int)

    ship_with_origin = shipping.merge(
        shipping_routes[["route_id", "origin_warehouse_id"]], on="route_id", how="left"
    )
    avg_delay_by_wh = (
        ship_with_origin.groupby("origin_warehouse_id")["delivery_delay_days"]
        .mean().round(2).rename("avg_delivery_delay_days")
    )
    df = df.merge(avg_delay_by_wh, left_on="warehouse_id", right_index=True, how="left")

    cols = ["warehouse_id", "warehouse_name", "country_id", "region_id", "warehouse_type",
            "capacity_units", "total_stock_units", "utilization_pct", "orders_fulfilled",
            "avg_delivery_delay_days"]
    return df[[c for c in cols if c in df.columns]]
