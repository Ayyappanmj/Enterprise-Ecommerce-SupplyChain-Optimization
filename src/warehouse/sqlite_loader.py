"""
Loads the star schema into a local SQLite file using nothing but the stdlib
(sqlite3) and pandas' built-in support for a raw sqlite3.Connection (no
SQLAlchemy needed). This is what this repo was actually built and tested
against - no MySQL server was available in the build environment. Swapping to
real MySQL is `WAREHOUSE_ENGINE=mysql` (see mysql_loader.py); the dimensional
model (schema_builder.py) is identical either way.

SQLite can't express every MySQL-ism in sql/schema.sql (AUTO_INCREMENT syntax,
ENGINE=InnoDB, some CHECK behavior), so this module creates an equivalent,
SQLite-flavored schema inline rather than executing sql/schema.sql directly.
"""
import os
import sqlite3

import pandas as pd

from .config import SQLITE_PATH
from src.utils.logging_setup import get_logger

logger = get_logger("warehouse.sqlite")

_DDL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS FactReturns;
DROP TABLE IF EXISTS FactShipping;
DROP TABLE IF EXISTS FactSales;
DROP TABLE IF EXISTS DimWarehouse;
DROP TABLE IF EXISTS DimProduct;
DROP TABLE IF EXISTS DimCustomer;
DROP TABLE IF EXISTS DimCountry;
DROP TABLE IF EXISTS DimDate;

CREATE TABLE DimDate (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE DimCountry (
    country_key INTEGER PRIMARY KEY,
    country_id TEXT NOT NULL UNIQUE,
    country_name TEXT NOT NULL,
    region_name TEXT NOT NULL,
    currency_code TEXT NOT NULL
);

CREATE TABLE DimCustomer (
    customer_key INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL UNIQUE,
    first_name TEXT, last_name TEXT, email TEXT, gender TEXT,
    segment TEXT, loyalty_tier TEXT,
    country_key INTEGER REFERENCES DimCountry(country_key),
    signup_date TEXT
);

CREATE TABLE DimProduct (
    product_key INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL UNIQUE,
    product_name TEXT, category TEXT, sub_category TEXT, supplier_id TEXT,
    unit_cost_usd REAL NOT NULL CHECK (unit_cost_usd >= 0),
    unit_price_usd REAL NOT NULL CHECK (unit_price_usd >= 0)
);

CREATE TABLE DimWarehouse (
    warehouse_key INTEGER PRIMARY KEY,
    warehouse_id TEXT NOT NULL UNIQUE,
    warehouse_name TEXT, warehouse_type TEXT,
    country_key INTEGER REFERENCES DimCountry(country_key),
    capacity_units INTEGER NOT NULL CHECK (capacity_units >= 0)
);

CREATE TABLE FactSales (
    sales_key INTEGER PRIMARY KEY AUTOINCREMENT,
    date_key INTEGER NOT NULL REFERENCES DimDate(date_key),
    order_id TEXT NOT NULL,
    order_item_id TEXT NOT NULL UNIQUE,
    customer_key INTEGER NOT NULL REFERENCES DimCustomer(customer_key),
    product_key INTEGER NOT NULL REFERENCES DimProduct(product_key),
    warehouse_key INTEGER NOT NULL REFERENCES DimWarehouse(warehouse_key),
    country_key INTEGER NOT NULL REFERENCES DimCountry(country_key),
    order_status TEXT,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    unit_price_usd REAL NOT NULL,
    unit_cost_usd REAL NOT NULL,
    line_discount_pct REAL NOT NULL DEFAULT 0,
    order_discount_pct REAL NOT NULL DEFAULT 0,
    line_total_usd REAL NOT NULL,
    line_net_revenue_usd REAL NOT NULL,
    line_cost_usd REAL NOT NULL,
    line_gross_profit_usd REAL NOT NULL,
    line_shipping_cost_usd REAL NOT NULL DEFAULT 0,
    is_cross_border INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sales_date ON FactSales(date_key);
CREATE INDEX idx_sales_customer ON FactSales(customer_key);
CREATE INDEX idx_sales_product ON FactSales(product_key);
CREATE INDEX idx_sales_warehouse ON FactSales(warehouse_key);
CREATE INDEX idx_sales_country ON FactSales(country_key);
CREATE INDEX idx_sales_order ON FactSales(order_id);

CREATE TABLE FactShipping (
    shipping_key INTEGER PRIMARY KEY AUTOINCREMENT,
    date_key INTEGER NOT NULL REFERENCES DimDate(date_key),
    shipping_id TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL,
    origin_warehouse_key INTEGER NOT NULL REFERENCES DimWarehouse(warehouse_key),
    destination_country_key INTEGER NOT NULL REFERENCES DimCountry(country_key),
    partner_id TEXT,
    route_id TEXT,
    standard_transit_days INTEGER,
    delivery_delay_days INTEGER,
    is_delayed INTEGER NOT NULL DEFAULT 0,
    shipping_status TEXT
);
CREATE INDEX idx_shipping_date ON FactShipping(date_key);
CREATE INDEX idx_shipping_warehouse ON FactShipping(origin_warehouse_key);
CREATE INDEX idx_shipping_country ON FactShipping(destination_country_key);
CREATE INDEX idx_shipping_order ON FactShipping(order_id);
CREATE INDEX idx_shipping_delay ON FactShipping(delivery_delay_days);

CREATE TABLE FactReturns (
    return_key INTEGER PRIMARY KEY AUTOINCREMENT,
    date_key INTEGER NOT NULL REFERENCES DimDate(date_key),
    return_id TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL,
    product_key INTEGER NOT NULL REFERENCES DimProduct(product_key),
    customer_key INTEGER NOT NULL REFERENCES DimCustomer(customer_key),
    warehouse_key INTEGER NOT NULL REFERENCES DimWarehouse(warehouse_key),
    country_key INTEGER NOT NULL REFERENCES DimCountry(country_key),
    return_reason TEXT, return_status TEXT, return_condition TEXT,
    refund_amount_usd REAL NOT NULL DEFAULT 0 CHECK (refund_amount_usd >= 0),
    is_cross_border INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_returns_date ON FactReturns(date_key);
CREATE INDEX idx_returns_product ON FactReturns(product_key);
CREATE INDEX idx_returns_customer ON FactReturns(customer_key);
CREATE INDEX idx_returns_warehouse ON FactReturns(warehouse_key);
CREATE INDEX idx_returns_country ON FactReturns(country_key);
CREATE INDEX idx_returns_order ON FactReturns(order_id);
"""


def load(tables: dict) -> None:
    """tables: dict of {table_name: DataFrame}, keys matching the DDL above."""
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)
        logger.info(f"Removed existing {SQLITE_PATH} for a clean reload")

    conn = sqlite3.connect(SQLITE_PATH)
    try:
        conn.executescript(_DDL)
        conn.commit()
        logger.info(f"Created star schema in {SQLITE_PATH}")

        load_order = ["DimDate", "DimCountry", "DimCustomer", "DimProduct", "DimWarehouse",
                      "FactSales", "FactShipping", "FactReturns"]
        for table_name in load_order:
            df = tables.get(table_name)
            if df is None:
                continue
            df.to_sql(table_name, conn, if_exists="append", index=False)
            logger.info(f"Loaded {len(df):,} row(s) into {table_name}")
        conn.commit()
    finally:
        conn.close()


def verify() -> dict:
    """Runs a couple of sanity queries (row counts + a join) against the
    loaded SQLite DB, so `run_load_warehouse.py` can prove the FKs actually
    resolve, not just that files got written."""
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        counts = {}
        for table in ["DimDate", "DimCountry", "DimCustomer", "DimProduct", "DimWarehouse",
                      "FactSales", "FactShipping", "FactReturns"]:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        orphan_check = conn.execute("""
            SELECT COUNT(*) FROM FactSales fs
            LEFT JOIN DimCustomer dc ON fs.customer_key = dc.customer_key
            LEFT JOIN DimProduct dp ON fs.product_key = dp.product_key
            WHERE dc.customer_key IS NULL OR dp.product_key IS NULL
        """).fetchone()[0]

        top_country = conn.execute("""
            SELECT c.country_name, ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit
            FROM FactSales fs JOIN DimCountry c ON fs.country_key = c.country_key
            GROUP BY c.country_name ORDER BY gross_profit DESC LIMIT 1
        """).fetchone()

        return {"row_counts": counts, "orphaned_fact_sales_rows": orphan_check, "top_country_by_gross_profit": top_country}
    finally:
        conn.close()
