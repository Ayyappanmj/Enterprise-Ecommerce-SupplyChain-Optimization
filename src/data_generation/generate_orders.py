"""Phase 1: Orders, Order_Items."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED, ORDER_DATE_START, ORDER_DATE_END
from .utils import zero_pad_id, random_dates


def generate(df_customers, df_countries, df_warehouses, df_products):
    rng = np.random.default_rng(SEED + 9)
    n = CFG["n_orders"]

    order_ids = zero_pad_id("ORD", range(1, n + 1), 8)
    customers = df_customers.sample(n, replace=True, random_state=SEED + 9).reset_index(drop=True)
    order_dates = random_dates(rng, ORDER_DATE_START, ORDER_DATE_END, n)
    warehouses = df_warehouses.sample(n, replace=True, random_state=SEED + 10).reset_index(drop=True)

    status = rng.choice(ref.ORDER_STATUSES, size=n, p=[0.70, 0.12, 0.05, 0.06, 0.07])
    payment_method = rng.choice(ref.PAYMENT_METHODS, size=n, p=[0.35, 0.20, 0.18, 0.10, 0.07, 0.10])
    discount_pct = np.round(rng.choice([0, 0, 0, 5, 10, 15, 20, 25], size=n) / 100, 2)

    orders_header = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customers["customer_id"].values,
        "order_date": order_dates,
        "warehouse_id": warehouses["warehouse_id"].values,
        "ship_country_id": customers["country_id"].values,
        "currency_code": customers["country_id"].map(
            df_countries.set_index("country_id")["currency_code"]
        ).values,
        "order_status": status,
        "payment_method": payment_method,
        "discount_pct": discount_pct,
    })

    # --- Order Items (vectorized, 1-5 items per order) ---
    n_items = rng.integers(1, 6, size=n)
    total_items = int(n_items.sum())
    order_id_repeated = np.repeat(orders_header["order_id"].values, n_items)

    products_sample = df_products.sample(total_items, replace=True, random_state=SEED + 11).reset_index(drop=True)
    quantity = rng.integers(1, 8, size=total_items)
    unit_price = products_sample["unit_price_usd"].values
    line_discount_pct = np.round(rng.choice([0, 0, 0, 5, 10], size=total_items) / 100, 2)
    line_total = np.round(quantity * unit_price * (1 - line_discount_pct), 2)

    order_items = pd.DataFrame({
        "order_item_id": zero_pad_id("OI", range(1, total_items + 1), 9),
        "order_id": order_id_repeated,
        "product_id": products_sample["product_id"].values,
        "quantity": quantity,
        "unit_price_usd": unit_price,
        "line_discount_pct": line_discount_pct,
        "line_total_usd": line_total,
    })

    # --- Roll item totals up into the order header ---
    subtotal = order_items.groupby("order_id")["line_total_usd"].sum().rename("subtotal_usd")
    orders_header = orders_header.merge(subtotal, on="order_id", how="left")

    shipping_cost = np.round(rng.gamma(shape=2.0, scale=6.0, size=n) + 2, 2)
    tax_rate = rng.uniform(0.04, 0.20, size=n)
    tax_amount = np.round(orders_header["subtotal_usd"].values * tax_rate, 2)
    order_discount_amt = np.round(orders_header["subtotal_usd"].values * orders_header["discount_pct"].values, 2)
    total_amount = np.round(
        orders_header["subtotal_usd"].values - order_discount_amt + shipping_cost + tax_amount, 2
    )

    orders_header["shipping_cost_usd"] = shipping_cost
    orders_header["tax_amount_usd"] = tax_amount
    orders_header["total_amount_usd"] = total_amount

    cols = ["order_id", "customer_id", "order_date", "warehouse_id", "ship_country_id", "currency_code",
            "order_status", "payment_method", "discount_pct", "subtotal_usd", "shipping_cost_usd",
            "tax_amount_usd", "total_amount_usd"]
    orders_header = orders_header[cols]

    orders_header.to_csv(os.path.join(RAW_DIR, "orders.csv"), index=False)
    order_items.to_csv(os.path.join(RAW_DIR, "order_items.csv"), index=False)
    print(f"orders: {len(orders_header)}, order_items: {len(order_items)}")
    return orders_header, order_items


if __name__ == "__main__":
    from .generate_geo_currency import generate as gen_geo
    from .generate_customers import generate as gen_customers
    from .generate_products import generate_suppliers, generate_products
    from .generate_logistics_network import generate_warehouses

    _, df_countries, _, _ = gen_geo()
    df_customers = gen_customers(df_countries)
    df_suppliers = generate_suppliers(df_countries)
    df_products = generate_products(df_suppliers)
    df_warehouses = generate_warehouses(df_countries)
    generate(df_customers, df_countries, df_warehouses, df_products)
