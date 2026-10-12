"""
Phase 6 - MySQL Data Warehouse.

Builds all 5 dimension + 3 fact tables (schema_builder.py, DB-agnostic) from
Phase 4's cleaned tables, then loads them into either:

    WAREHOUSE_ENGINE=sqlite (default) - a local file at data/warehouse/warehouse.db,
        zero dependencies, what this repo was actually tested against.
    WAREHOUSE_ENGINE=mysql - a real MySQL 8.0+ server, via SQLAlchemy+PyMySQL.

Usage:
    python -m src.warehouse.run_load_warehouse                    # sqlite
    python -m src.warehouse.run_load_warehouse --engine mysql
"""
import argparse
import os
import time

import pandas as pd

from src.cleaning.config import CLEANED_DIR
from .config import WAREHOUSE_ENGINE
from . import schema_builder
from src.utils.logging_setup import get_logger

logger = get_logger("warehouse.run")


def _load_cleaned(table_name: str) -> pd.DataFrame:
    path = os.path.join(CLEANED_DIR, f"{table_name}_clean.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run `python -m src.cleaning.run_cleaning` first (Phase 4).")
    return pd.read_csv(path)


def build_all_tables() -> dict:
    logger.info("Loading Phase 4 cleaned tables...")
    countries = _load_cleaned("countries")
    regions = _load_cleaned("regions")
    customers = _load_cleaned("customers")
    products = _load_cleaned("products")
    warehouses = _load_cleaned("warehouses")
    orders = _load_cleaned("orders")
    order_items = _load_cleaned("order_items")
    shipping = _load_cleaned("shipping")
    shipping_routes = _load_cleaned("shipping_routes")
    returns = _load_cleaned("returns")

    logger.info("Building dimensions...")
    dim_country = schema_builder.build_dim_country(countries, regions)
    dim_customer = schema_builder.build_dim_customer(customers, dim_country)
    dim_product = schema_builder.build_dim_product(products)
    dim_warehouse = schema_builder.build_dim_warehouse(warehouses, dim_country)

    all_dates = pd.concat([
        pd.to_datetime(orders["order_date"]),
        pd.to_datetime(shipping["ship_date"]),
        pd.to_datetime(returns["return_date"]),
    ])
    dim_date = schema_builder.build_dim_date(all_dates)

    logger.info("Building facts...")
    fact_sales = schema_builder.build_fact_sales(orders, order_items, dim_customer, dim_product,
                                                  dim_warehouse, dim_country)
    fact_shipping = schema_builder.build_fact_shipping(shipping, shipping_routes, dim_warehouse, dim_country)
    fact_returns = schema_builder.build_fact_returns(returns, order_items, orders, dim_product, dim_customer,
                                                    dim_warehouse, dim_country)

    return {
        "DimDate": dim_date, "DimCountry": dim_country, "DimCustomer": dim_customer,
        "DimProduct": dim_product, "DimWarehouse": dim_warehouse,
        "FactSales": fact_sales, "FactShipping": fact_shipping, "FactReturns": fact_returns,
    }


def main(engine_name: str = None):
    t0 = time.time()
    engine_name = (engine_name or WAREHOUSE_ENGINE).lower()
    logger.info(f"=== Loading warehouse (engine={engine_name}) ===")

    tables = build_all_tables()
    for name, df in tables.items():
        logger.info(f"  built {name}: {len(df):,} rows")

    if engine_name == "sqlite":
        from . import sqlite_loader as loader
    elif engine_name == "mysql":
        from . import mysql_loader as loader
        loader.create_schema()
    else:
        raise ValueError(f"Unknown WAREHOUSE_ENGINE '{engine_name}'. Use sqlite or mysql.")

    loader.load(tables)
    verification = loader.verify()

    logger.info(f"=== Warehouse load complete in {time.time() - t0:.1f}s ===")
    print("\n=== Row counts ===")
    for t, n in verification["row_counts"].items():
        print(f"  {t:15}: {n:,}")
    if "orphaned_fact_sales_rows" in verification:
        print(f"\nOrphaned FactSales rows (should be 0): {verification['orphaned_fact_sales_rows']}")
    print(f"Top country by gross profit: {verification['top_country_by_gross_profit']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the star-schema warehouse")
    parser.add_argument("--engine", choices=["sqlite", "mysql"], default=None)
    args = parser.parse_args()
    main(args.engine)
