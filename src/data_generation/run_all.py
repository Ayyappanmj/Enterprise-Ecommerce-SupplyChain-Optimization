"""
Generate the full enterprise dataset (all 15 tables) in dependency order.

Usage:
    python -m src.data_generation.run_all              # full scale (500K orders etc.)
    DATA_SCALE=sample python -m src.data_generation.run_all   # small/fast dataset for dev

Output: CSV files written to data/raw/
"""
import time

from .config import CFG, SCALE, RAW_DIR
from .generate_geo_currency import generate as gen_geo_currency
from .generate_customers import generate as gen_customers
from .generate_products import generate_suppliers, generate_products
from .generate_logistics_network import (
    generate_warehouses, generate_logistics_partners, generate_shipping_routes,
)
from .generate_orders import generate as gen_orders
from .generate_inventory_shipping import generate_inventory, generate_shipping
from .generate_returns_payments_marketing import (
    generate_returns, generate_payments, generate_marketing_campaigns,
)


def main():
    t0 = time.time()
    print(f"=== Generating dataset at scale='{SCALE}' -> {RAW_DIR} ===")
    print(f"Config: {CFG}\n")

    df_regions, df_countries, df_currencies, df_fx = gen_geo_currency()
    df_customers = gen_customers(df_countries)
    df_suppliers = generate_suppliers(df_countries)
    df_products = generate_products(df_suppliers)
    df_warehouses = generate_warehouses(df_countries)
    df_partners = generate_logistics_partners(df_countries)
    df_routes = generate_shipping_routes(df_warehouses, df_countries, df_partners)

    df_orders, df_order_items = gen_orders(df_customers, df_countries, df_warehouses, df_products)

    generate_inventory(df_warehouses, df_products)
    generate_shipping(df_orders, df_routes)
    generate_returns(df_orders, df_order_items)
    generate_payments(df_orders)
    generate_marketing_campaigns(df_regions, df_countries)

    print(f"\n=== Done in {time.time() - t0:.1f}s. 15 CSV files written to {RAW_DIR} ===")


if __name__ == "__main__":
    main()
