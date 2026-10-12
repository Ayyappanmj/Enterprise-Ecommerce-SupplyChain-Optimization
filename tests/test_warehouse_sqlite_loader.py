"""
Tests sqlite_loader.py against a REAL temporary SQLite file (not a mock) -
this is the same code path used to build the 1.5M-row warehouse in Phase 6,
just at a scale a unit test can run in milliseconds.
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.warehouse import sqlite_loader


def _tiny_tables():
    dim_date = pd.DataFrame({
        "date_key": [20240101], "full_date": ["2024-01-01"], "year": [2024], "quarter": [1],
        "month": [1], "month_name": ["January"], "day": [1], "day_of_week": [0],
        "day_name": ["Monday"], "is_weekend": [False],
    })
    dim_country = pd.DataFrame({
        "country_key": [1], "country_id": ["CTY001"], "country_name": ["USA"],
        "region_name": ["North America"], "currency_code": ["USD"],
    })
    dim_customer = pd.DataFrame({
        "customer_key": [1], "customer_id": ["C1"], "first_name": ["Jane"], "last_name": ["Doe"],
        "email": ["j@example.com"], "gender": ["Female"], "segment": ["Consumer"],
        "loyalty_tier": ["Gold"], "country_key": [1], "signup_date": ["2023-01-01"],
    })
    dim_product = pd.DataFrame({
        "product_key": [1], "product_id": ["P1"], "product_name": ["Widget"], "category": ["Tools"],
        "sub_category": ["Hand Tools"], "supplier_id": ["SUP1"], "unit_cost_usd": [5.0], "unit_price_usd": [10.0],
    })
    dim_warehouse = pd.DataFrame({
        "warehouse_key": [1], "warehouse_id": ["WH1"], "warehouse_name": ["Main WH"],
        "warehouse_type": ["Fulfillment Center"], "country_key": [1], "capacity_units": [100000],
    })
    fact_sales = pd.DataFrame({
        "date_key": [20240101], "order_id": ["ORD1"], "order_item_id": ["OI1"], "customer_key": [1],
        "product_key": [1], "warehouse_key": [1], "country_key": [1], "order_status": ["Delivered"],
        "quantity": [2], "unit_price_usd": [10.0], "unit_cost_usd": [5.0], "line_discount_pct": [0.0],
        "order_discount_pct": [0.0], "line_total_usd": [20.0], "line_net_revenue_usd": [20.0],
        "line_cost_usd": [10.0], "line_gross_profit_usd": [10.0], "line_shipping_cost_usd": [2.0],
        "is_cross_border": [0],
    })
    fact_shipping = pd.DataFrame({
        "date_key": [20240101], "shipping_id": ["SHP1"], "order_id": ["ORD1"], "origin_warehouse_key": [1],
        "destination_country_key": [1], "partner_id": ["LOG1"], "route_id": ["RT1"],
        "standard_transit_days": [3], "delivery_delay_days": [1], "is_delayed": [0],
        "shipping_status": ["Delivered"],
    })
    fact_returns = pd.DataFrame({
        "date_key": [20240101], "return_id": ["RET1"], "order_id": ["ORD1"], "product_key": [1],
        "customer_key": [1], "warehouse_key": [1], "country_key": [1], "return_reason": ["Defective Product"],
        "return_status": ["Refunded"], "return_condition": ["Opened - Like New"], "refund_amount_usd": [10.0],
        "is_cross_border": [0],
    })
    return {
        "DimDate": dim_date, "DimCountry": dim_country, "DimCustomer": dim_customer,
        "DimProduct": dim_product, "DimWarehouse": dim_warehouse,
        "FactSales": fact_sales, "FactShipping": fact_shipping, "FactReturns": fact_returns,
    }


class TestSqliteLoader(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_warehouse.db")
        self.patcher = patch.object(sqlite_loader, "SQLITE_PATH", self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()

    def test_load_creates_all_tables_with_correct_row_counts(self):
        sqlite_loader.load(_tiny_tables())
        conn = sqlite3.connect(self.db_path)
        for table in ["DimDate", "DimCountry", "DimCustomer", "DimProduct", "DimWarehouse",
                      "FactSales", "FactShipping", "FactReturns"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            self.assertEqual(count, 1, f"{table} should have exactly 1 row")
        conn.close()

    def test_foreign_keys_actually_resolve(self):
        sqlite_loader.load(_tiny_tables())
        conn = sqlite3.connect(self.db_path)
        orphans = conn.execute("""
            SELECT COUNT(*) FROM FactSales fs
            LEFT JOIN DimCustomer dc ON fs.customer_key = dc.customer_key
            LEFT JOIN DimProduct dp ON fs.product_key = dp.product_key
            LEFT JOIN DimWarehouse dw ON fs.warehouse_key = dw.warehouse_key
            LEFT JOIN DimCountry co ON fs.country_key = co.country_key
            WHERE dc.customer_key IS NULL OR dp.product_key IS NULL
               OR dw.warehouse_key IS NULL OR co.country_key IS NULL
        """).fetchone()[0]
        self.assertEqual(orphans, 0)
        conn.close()

    def test_verify_returns_correct_row_counts_and_top_country(self):
        sqlite_loader.load(_tiny_tables())
        result = sqlite_loader.verify()
        self.assertEqual(result["row_counts"]["FactSales"], 1)
        self.assertEqual(result["orphaned_fact_sales_rows"], 0)
        self.assertEqual(result["top_country_by_gross_profit"][0], "USA")
        self.assertAlmostEqual(result["top_country_by_gross_profit"][1], 10.0)

    def test_reload_replaces_rather_than_duplicates(self):
        sqlite_loader.load(_tiny_tables())
        sqlite_loader.load(_tiny_tables())  # simulate a re-run of the pipeline
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM FactSales").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)  # the DB file is removed and rebuilt, not appended to

    def test_schema_enforces_quantity_check_constraint(self):
        sqlite_loader.load(_tiny_tables())
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO FactSales (date_key, order_id, order_item_id, customer_key, product_key,
                    warehouse_key, country_key, quantity, unit_price_usd, unit_cost_usd, line_total_usd,
                    line_net_revenue_usd, line_cost_usd, line_gross_profit_usd)
                VALUES (20240101, 'ORD2', 'OI2', 1, 1, 1, 1, -5, 10.0, 5.0, 20.0, 20.0, 10.0, 10.0)
            """)
        conn.close()


if __name__ == "__main__":
    unittest.main()
