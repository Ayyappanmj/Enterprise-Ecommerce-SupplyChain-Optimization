import unittest

import pandas as pd

from src.etl import validators
from src.etl.exceptions import ValidationError


class TestValidateWebOrders(unittest.TestCase):
    def _valid_df(self):
        return pd.DataFrame({
            "order_id": ["ORD1", "ORD2", "ORD3"],
            "customer_id": ["C1", "C2", "C3"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "total_amount_usd": [100.0, 200.0, 50.0],
            "order_status": ["Delivered", "Shipped", "Processing"],
        })

    def test_clean_input_all_valid(self):
        good, bad, issues = validators.validate_web_orders(self._valid_df())
        self.assertEqual(len(good), 3)
        self.assertEqual(len(bad), 0)
        self.assertEqual(issues, [])

    def test_quarantines_duplicate_order_id(self):
        df = self._valid_df()
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # duplicate ORD1
        good, bad, issues = validators.validate_web_orders(df)
        self.assertEqual(len(good), 3)
        self.assertEqual(len(bad), 1)
        self.assertIn("duplicate order_id", issues[0])

    def test_quarantines_null_customer_id(self):
        df = self._valid_df()
        df.loc[1, "customer_id"] = None
        good, bad, issues = validators.validate_web_orders(df)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 1)

    def test_quarantines_negative_total(self):
        df = self._valid_df()
        df.loc[2, "total_amount_usd"] = -50.0
        good, bad, issues = validators.validate_web_orders(df)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 1)

    def test_missing_required_column_raises(self):
        df = self._valid_df().drop(columns=["order_status"])
        with self.assertRaises(ValidationError):
            validators.validate_web_orders(df)


class TestValidateInventory(unittest.TestCase):
    def _valid_df(self):
        return pd.DataFrame({
            "inventory_id": ["INV1", "INV2"],
            "warehouse_id": ["WH1", "WH2"],
            "product_id": ["P1", "P2"],
            "stock_quantity": [100, 200],
        })

    def test_quarantines_negative_stock(self):
        df = self._valid_df()
        df.loc[0, "stock_quantity"] = -5
        good, bad, issues = validators.validate_inventory(df)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(bad), 1)

    def test_quarantines_null_warehouse(self):
        df = self._valid_df()
        df.loc[1, "warehouse_id"] = None
        good, bad, issues = validators.validate_inventory(df)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(bad), 1)


class TestValidateShipping(unittest.TestCase):
    def _valid_df(self):
        return pd.DataFrame({
            "shipping_id": ["SHP1", "SHP2"],
            "order_id": ["ORD1", "ORD2"],
            "ship_date": ["2024-01-01", "2024-01-05"],
            "shipping_status": ["Delivered", "In Transit"],
            "actual_delivery_date": ["2024-01-05", None],
        })

    def test_quarantines_delivery_before_ship(self):
        df = self._valid_df()
        df.loc[0, "actual_delivery_date"] = "2023-12-25"  # before ship_date -> impossible
        good, bad, issues = validators.validate_shipping(df)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(bad), 1)

    def test_null_delivery_date_is_not_flagged_as_impossible(self):
        # a shipment still in transit legitimately has no delivery date yet
        good, bad, issues = validators.validate_shipping(self._valid_df())
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 0)


if __name__ == "__main__":
    unittest.main()
