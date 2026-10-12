"""
Phase 5 - Feature Engineering.

Reads Phase 4's cleaned tables (data/processed/cleaned/) and builds:
    fact_order_features.csv        - Gross Margin, Net Margin, profit, per order
    fact_shipping_features.csv     - Shipping Delay, per shipment
    dim_customer_features.csv      - Customer Lifetime Value, AOV, repeat-purchase flag
    dim_product_features.csv       - product-level margin, Return Rate
    dim_warehouse_features.csv     - Warehouse Utilization
    country_profit_summary.csv     - Profit by Country
    kpi_summary.json / .csv        - single-row executive rollup of all the above

Usage:
    python -m src.feature_engineering.run_feature_engineering
"""
import json
import os
import time

import pandas as pd

from . import data_loader
from .config import FEATURES_DIR, REPORTS_DIR
from . import order_features, shipping_features, customer_features, product_features, country_features, kpi_summary
from src.utils.logging_setup import get_logger

logger = get_logger("features.run")


def main():
    t0 = time.time()
    logger.info("=== Feature engineering starting ===")

    orders = data_loader.load("orders")
    order_items = data_loader.load("order_items")
    products = data_loader.load("products")
    customers = data_loader.load("customers")
    countries = data_loader.load("countries")
    regions = data_loader.load("regions")
    warehouses = data_loader.load("warehouses")
    inventory = data_loader.load("inventory")
    shipping = data_loader.load("shipping")
    shipping_routes = data_loader.load("shipping_routes")
    returns = data_loader.load("returns")

    logger.info("Building order-level features (Gross Margin, Net Margin)...")
    order_feat = order_features.build(orders, order_items, products, returns)
    order_feat.to_csv(os.path.join(FEATURES_DIR, "fact_order_features.csv"), index=False)

    logger.info("Building shipping features (Shipping Delay) + warehouse utilization...")
    ship_feat = shipping_features.build_shipping_delay_features(shipping)
    ship_feat.to_csv(os.path.join(FEATURES_DIR, "fact_shipping_features.csv"), index=False)

    wh_feat = shipping_features.build_warehouse_utilization(inventory, warehouses, orders, shipping, shipping_routes)
    wh_feat.to_csv(os.path.join(FEATURES_DIR, "dim_warehouse_features.csv"), index=False)

    logger.info("Building customer features (CLV, AOV, Repeat Purchase Rate)...")
    cust_feat = customer_features.build(customers, orders)
    cust_feat.to_csv(os.path.join(FEATURES_DIR, "dim_customer_features.csv"), index=False)

    logger.info("Building product features (margin, Return Rate)...")
    prod_feat = product_features.build(products, order_items, returns)
    prod_feat.to_csv(os.path.join(FEATURES_DIR, "dim_product_features.csv"), index=False)

    logger.info("Building country profit summary (Profit by Country)...")
    country_feat = country_features.build(order_feat, countries, regions, shipping)
    country_feat.to_csv(os.path.join(FEATURES_DIR, "country_profit_summary.csv"), index=False)

    logger.info("Rolling up executive KPI summary...")
    kpis = kpi_summary.build(order_feat, cust_feat, ship_feat)
    with open(os.path.join(REPORTS_DIR, "kpi_summary.json"), "w") as f:
        json.dump(kpis, f, indent=2)
    pd.DataFrame([kpis]).to_csv(os.path.join(REPORTS_DIR, "kpi_summary.csv"), index=False)

    logger.info(f"=== Feature engineering complete in {time.time() - t0:.1f}s -> {FEATURES_DIR} ===")
    print("\n=== Executive KPI Summary ===")
    for k, v in kpis.items():
        print(f"{k:35}: {v}")
    print("\nTop 5 countries by net profit:")
    print(country_feat[["country_name", "num_orders", "net_profit_usd", "net_margin_pct"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
