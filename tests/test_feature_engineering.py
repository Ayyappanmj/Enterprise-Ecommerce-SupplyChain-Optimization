import unittest

import pandas as pd

from src.feature_engineering import order_features, customer_features
from src.feature_engineering.config import ASSUMED_OPEX_RATE


class TestOrderFeatures(unittest.TestCase):
    def setUp(self):
        # One order, two line items. Hand-calculated expectations below.
        self.orders = pd.DataFrame({
            "order_id": ["ORD1"],
            "customer_id": ["C1"],
            "warehouse_id": ["WH1"],
            "ship_country_id": ["CTY1"],
            "order_date": ["2024-01-01"],
            "order_status": ["Delivered"],
            "currency_code": ["USD"],
            "discount_pct": [0.10],          # 10% order-level discount
            "subtotal_usd": [100.0],          # sum of line_total_usd below
            "shipping_cost_usd": [5.0],
            "tax_amount_usd": [8.0],
            "total_amount_usd": [103.0],
        })
        self.order_items = pd.DataFrame({
            "order_item_id": ["OI1", "OI2"],
            "order_id": ["ORD1", "ORD1"],
            "product_id": ["P1", "P2"],
            "quantity": [2, 1],
            "unit_price_usd": [30.0, 40.0],
            "line_discount_pct": [0.0, 0.0],
            "line_total_usd": [60.0, 40.0],    # sums to subtotal_usd = 100
        })
        self.products = pd.DataFrame({
            "product_id": ["P1", "P2"],
            "unit_cost_usd": [10.0, 25.0],      # COGS: 2*10 + 1*25 = 45
        })
        self.returns_empty = pd.DataFrame(columns=["order_id", "refund_amount_usd"])

    def test_revenue_and_cogs_and_gross_profit(self):
        out = order_features.build(self.orders, self.order_items, self.products, self.returns_empty)
        row = out.iloc[0]
        # product_revenue = subtotal * (1 - discount) = 100 * 0.9 = 90
        self.assertAlmostEqual(row["product_revenue_usd"], 90.0)
        self.assertAlmostEqual(row["cogs_usd"], 45.0)
        self.assertAlmostEqual(row["gross_profit_usd"], 45.0)   # 90 - 45
        self.assertAlmostEqual(row["gross_margin_pct"], 0.5)     # 45 / 90

    def test_net_profit_uses_configured_opex_rate(self):
        out = order_features.build(self.orders, self.order_items, self.products, self.returns_empty)
        row = out.iloc[0]
        expected_opex = 90.0 * ASSUMED_OPEX_RATE
        expected_net_profit = 45.0 - 5.0 - 0.0 - expected_opex  # gross_profit - shipping - refunds - opex
        self.assertAlmostEqual(row["opex_usd"], expected_opex, places=2)
        self.assertAlmostEqual(row["net_profit_usd"], expected_net_profit, places=2)

    def test_is_returned_flag_and_refund_allocation(self):
        returns = pd.DataFrame({"order_id": ["ORD1"], "refund_amount_usd": [20.0]})
        out = order_features.build(self.orders, self.order_items, self.products, returns)
        row = out.iloc[0]
        self.assertTrue(row["is_returned"])
        self.assertAlmostEqual(row["refund_amount_usd"], 20.0)

    def test_order_with_no_return_is_not_flagged(self):
        out = order_features.build(self.orders, self.order_items, self.products, self.returns_empty)
        self.assertFalse(out.iloc[0]["is_returned"])
        self.assertAlmostEqual(out.iloc[0]["refund_amount_usd"], 0.0)

    def test_zero_revenue_order_does_not_divide_by_zero(self):
        orders = self.orders.copy()
        orders["discount_pct"] = 1.0  # 100% discount -> zero product revenue
        out = order_features.build(orders, self.order_items, self.products, self.returns_empty)
        self.assertAlmostEqual(out.iloc[0]["product_revenue_usd"], 0.0)
        self.assertTrue(pd.isna(out.iloc[0]["gross_margin_pct"]))  # NaN, not a crash


class TestCustomerFeatures(unittest.TestCase):
    def setUp(self):
        self.customers = pd.DataFrame({
            "customer_id": ["C1", "C2"],
            "country_id": ["CTY1", "CTY1"],
            "segment": ["Consumer", "Consumer"],
            "loyalty_tier": ["Gold", "Bronze"],
            "signup_date": ["2023-01-01", "2023-01-01"],
        })
        self.orders = pd.DataFrame({
            "order_id": ["O1", "O2", "O3"],
            "customer_id": ["C1", "C1", "C2"],
            # Parsed to datetime here because the real pipeline's data_loader.py
            # always parses order_date before calling build() - customer_features
            # relies on that and isn't responsible for re-parsing it itself.
            "order_date": pd.to_datetime(["2024-01-01", "2024-03-01", "2024-01-01"]),
            "total_amount_usd": [100.0, 200.0, 50.0],
        })

    def test_clv_and_aov_per_customer(self):
        out = customer_features.build(self.customers, self.orders)
        c1 = out[out["customer_id"] == "C1"].iloc[0]
        self.assertEqual(c1["num_orders"], 2)
        self.assertAlmostEqual(c1["clv_historical_usd"], 300.0)
        self.assertAlmostEqual(c1["avg_order_value_usd"], 150.0)
        self.assertTrue(c1["is_repeat_customer"])

    def test_single_order_customer_is_not_repeat_and_has_no_projection(self):
        out = customer_features.build(self.customers, self.orders)
        c2 = out[out["customer_id"] == "C2"].iloc[0]
        self.assertEqual(c2["num_orders"], 1)
        self.assertFalse(c2["is_repeat_customer"])
        self.assertTrue(pd.isna(c2["projected_clv_usd"]))  # can't estimate frequency from n=1

    def test_overall_repeat_purchase_rate(self):
        out = customer_features.build(self.customers, self.orders)
        rate = customer_features.overall_repeat_purchase_rate(out)
        self.assertAlmostEqual(rate, 0.5)  # 1 of 2 purchasing customers is a repeat buyer

    def test_customer_with_zero_orders_is_not_counted_as_repeat(self):
        customers = pd.concat([self.customers, pd.DataFrame({
            "customer_id": ["C3"], "country_id": ["CTY1"], "segment": ["Consumer"],
            "loyalty_tier": ["Bronze"], "signup_date": ["2023-01-01"],
        })], ignore_index=True)
        out = customer_features.build(customers, self.orders)
        c3 = out[out["customer_id"] == "C3"].iloc[0]
        self.assertEqual(c3["num_orders"], 0)
        self.assertFalse(c3["is_repeat_customer"])


if __name__ == "__main__":
    unittest.main()
