"""Phase 1: Inventory, Shipping."""
import numpy as np
import pandas as pd
import os

from .config import CFG, RAW_DIR, SEED, ORDER_DATE_END
from .utils import zero_pad_id, random_dates


def generate_inventory(df_warehouses, df_products):
    rng = np.random.default_rng(SEED + 12)
    n = CFG["n_inventory_records"]
    wh = df_warehouses["warehouse_id"].sample(n, replace=True, random_state=SEED + 12).values
    prod = df_products["product_id"].sample(n, replace=True, random_state=SEED + 13).values

    df = pd.DataFrame({
        "inventory_id": zero_pad_id("INV", range(1, n + 1), 8),
        "warehouse_id": wh,
        "product_id": prod,
        "stock_quantity": rng.integers(0, 5000, size=n),
        "reorder_level": rng.integers(50, 500, size=n),
        "last_restock_date": random_dates(rng, "2024-01-01", ORDER_DATE_END, n).date,
    }).drop_duplicates(subset=["warehouse_id", "product_id"])

    df.to_csv(os.path.join(RAW_DIR, "inventory.csv"), index=False)
    print(f"inventory: {len(df)}")
    return df


def generate_shipping(df_orders, df_shipping_routes):
    rng = np.random.default_rng(SEED + 14)
    shippable = df_orders[df_orders["order_status"].isin(["Shipped", "Delivered", "Returned"])].reset_index(drop=True)
    n = len(shippable)

    routes = df_shipping_routes.sample(n, replace=True, random_state=SEED + 14).reset_index(drop=True)
    ship_date = pd.to_datetime(shippable["order_date"]) + pd.to_timedelta(rng.integers(0, 3, size=n), unit="D")
    promised_transit = routes["standard_transit_days"].values
    promised_delivery = ship_date + pd.to_timedelta(promised_transit, unit="D")

    # Delay model: ~60% on time or early, ~40% delayed by 1-15 days
    is_delayed = rng.random(n) < 0.40
    delay_days = np.where(is_delayed, rng.integers(1, 15, size=n), rng.integers(-2, 1, size=n))
    actual_delivery = promised_delivery + pd.to_timedelta(delay_days, unit="D")

    shipping_status = np.where(
        shippable["order_status"].values == "Delivered", "Delivered",
        np.where(shippable["order_status"].values == "Returned", "Delivered - Returned", "In Transit"),
    )

    df = pd.DataFrame({
        "shipping_id": zero_pad_id("SHP", range(1, n + 1), 8),
        "order_id": shippable["order_id"].values,
        "route_id": routes["route_id"].values,
        "partner_id": routes["partner_id"].values,
        "ship_date": ship_date,
        "promised_delivery_date": promised_delivery,
        "actual_delivery_date": actual_delivery,
        "delivery_delay_days": delay_days,
        "shipping_status": shipping_status,
    })
    df.to_csv(os.path.join(RAW_DIR, "shipping.csv"), index=False)
    print(f"shipping: {len(df)}")
    return df


if __name__ == "__main__":
    print("Run via run_all.py so upstream tables (warehouses/products/orders/routes) are available.")
