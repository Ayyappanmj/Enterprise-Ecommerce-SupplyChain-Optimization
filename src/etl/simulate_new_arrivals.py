"""
Appends a small batch of "new" rows (timestamped now) to the raw sources, so
you can demonstrate incremental loading end-to-end:

    python -m src.etl.run_pipeline              # run 1: loads everything
    python -m src.etl.simulate_new_arrivals      # a new day's data "arrives"
    python -m src.etl.run_pipeline               # run 2: loads ONLY the new rows

This only touches data/raw/ (the source systems); it never touches
data/processed/ directly - that's the pipeline's job.
"""
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import RAW_DIR
from src.utils.logging_setup import get_logger

logger = get_logger("etl.simulate_new_arrivals")

N_NEW_ORDERS = 25
N_INVENTORY_UPDATES = 15
N_NEW_SHIPMENTS = 20


def simulate_new_orders():
    orders_path = os.path.join(RAW_DIR, "orders.csv")
    customers_path = os.path.join(RAW_DIR, "customers.csv")
    warehouses_path = os.path.join(RAW_DIR, "warehouses.csv")
    countries_path = os.path.join(RAW_DIR, "countries.csv")

    orders = pd.read_csv(orders_path)
    customers = pd.read_csv(customers_path)
    warehouses = pd.read_csv(warehouses_path)
    countries = pd.read_csv(countries_path).set_index("country_id")["currency_code"]

    rng = np.random.default_rng()
    n = N_NEW_ORDERS
    last_num = orders["order_id"].str.replace("ORD", "", regex=False).astype(int).max()
    new_ids = [f"ORD{n_:08d}" for n_ in range(last_num + 1, last_num + 1 + n)]

    cust_sample = customers.sample(n, replace=True)
    wh_sample = warehouses.sample(n, replace=True)
    now = datetime.now(timezone.utc)

    subtotal = np.round(rng.gamma(2.0, 40, size=n), 2)
    shipping_cost = np.round(rng.gamma(2.0, 6.0, size=n) + 2, 2)
    tax = np.round(subtotal * rng.uniform(0.05, 0.18, size=n), 2)
    discount_pct = np.round(rng.choice([0, 0, 5, 10], size=n) / 100, 2)

    new_orders = pd.DataFrame({
        "order_id": new_ids,
        "customer_id": cust_sample["customer_id"].values,
        "order_date": [now.strftime("%Y-%m-%d %H:%M:%S")] * n,
        "warehouse_id": wh_sample["warehouse_id"].values,
        "ship_country_id": cust_sample["country_id"].values,
        "currency_code": cust_sample["country_id"].map(countries).values,
        "order_status": rng.choice(["Processing", "Shipped"], size=n),
        "payment_method": rng.choice(["Credit Card", "PayPal", "Digital Wallet"], size=n),
        "discount_pct": discount_pct,
        "subtotal_usd": subtotal,
        "shipping_cost_usd": shipping_cost,
        "tax_amount_usd": tax,
        "total_amount_usd": np.round(subtotal * (1 - discount_pct) + shipping_cost + tax, 2),
    })
    new_orders.to_csv(orders_path, mode="a", header=False, index=False)
    logger.info(f"Simulated {n} new web orders dated {now.isoformat()}")
    return new_orders


def simulate_inventory_updates():
    inv_path = os.path.join(RAW_DIR, "inventory.csv")
    inv = pd.read_csv(inv_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    idx = inv.sample(min(N_INVENTORY_UPDATES, len(inv))).index
    rng = np.random.default_rng()
    inv.loc[idx, "last_restock_date"] = now
    inv.loc[idx, "stock_quantity"] = rng.integers(500, 5000, size=len(idx))
    inv.to_csv(inv_path, index=False)
    logger.info(f"Simulated restock for {len(idx)} inventory rows dated {now}")


def simulate_new_shipments():
    shipping_path = os.path.join(RAW_DIR, "shipping.csv")
    orders_path = os.path.join(RAW_DIR, "orders.csv")
    routes_path = os.path.join(RAW_DIR, "shipping_routes.csv")

    shipping = pd.read_csv(shipping_path)
    orders = pd.read_csv(orders_path).tail(200)  # bias toward recently created orders
    routes = pd.read_csv(routes_path)

    n = N_NEW_SHIPMENTS
    last_num = shipping["shipping_id"].str.replace("SHP", "", regex=False).astype(int).max()
    new_ids = [f"SHP{n_:08d}" for n_ in range(last_num + 1, last_num + 1 + n)]

    order_sample = orders.sample(n, replace=True)
    route_sample = routes.sample(n, replace=True)
    now = datetime.now(timezone.utc)
    promised = now + pd.to_timedelta(route_sample["standard_transit_days"].values, unit="D")

    new_shipping = pd.DataFrame({
        "shipping_id": new_ids,
        "order_id": order_sample["order_id"].values,
        "route_id": route_sample["route_id"].values,
        "partner_id": route_sample["partner_id"].values,
        "ship_date": [now.strftime("%Y-%m-%d %H:%M:%S")] * n,
        "promised_delivery_date": promised.strftime("%Y-%m-%d %H:%M:%S"),
        "actual_delivery_date": [""] * n,
        "delivery_delay_days": [0] * n,
        "shipping_status": ["In Transit"] * n,
    })
    new_shipping.to_csv(shipping_path, mode="a", header=False, index=False)
    logger.info(f"Simulated {n} new shipments dated {now.isoformat()} (mock API will pick these up)")


def main():
    logger.info("=== Simulating a new day's arrivals across all 3 sources ===")
    simulate_new_orders()
    simulate_inventory_updates()
    simulate_new_shipments()
    logger.info("=== Done. Re-run `python -m src.etl.run_pipeline` to load only these new rows. ===")


if __name__ == "__main__":
    main()
