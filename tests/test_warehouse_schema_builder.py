import unittest

import pandas as pd

from src.warehouse import schema_builder as sb


class TestBuildDimDate(unittest.TestCase):
    def test_covers_every_day_in_range_with_no_gaps(self):
        dates = pd.Series(["2024-01-01", "2024-01-05"])
        dim = sb.build_dim_date(dates)
        self.assertEqual(len(dim), 5)  # Jan 1..5 inclusive
        self.assertEqual(dim["date_key"].iloc[0], 20240101)
        self.assertEqual(dim["date_key"].iloc[-1], 20240105)

    def test_weekend_flag_is_correct(self):
        # 2024-01-06 and 2024-01-07 are a Saturday and Sunday.
        dates = pd.Series(["2024-01-05", "2024-01-08"])
        dim = sb.build_dim_date(dates)
        weekends = dim[dim["full_date"].isin(pd.to_datetime(["2024-01-06", "2024-01-07"]))]
        self.assertTrue(weekends["is_weekend"].all())
        weekdays = dim[dim["full_date"] == pd.Timestamp("2024-01-05")]
        self.assertFalse(weekdays["is_weekend"].iloc[0])


class TestDateToKey(unittest.TestCase):
    def test_formats_as_yyyymmdd_integer(self):
        out = sb.date_to_key(pd.Series(["2024-03-07"]))
        self.assertEqual(out.iloc[0], 20240307)


class TestBuildDimCountry(unittest.TestCase):
    def test_assigns_sequential_surrogate_keys(self):
        countries = pd.DataFrame({
            "country_id": ["CTY001", "CTY002"], "country_name": ["USA", "Canada"],
            "region_id": ["REG01", "REG01"], "currency_code": ["USD", "CAD"],
        })
        regions = pd.DataFrame({"region_id": ["REG01"], "region_name": ["North America"]})
        dim = sb.build_dim_country(countries, regions)
        self.assertEqual(list(dim["country_key"]), [1, 2])
        self.assertEqual(dim[dim["country_id"] == "CTY001"]["region_name"].iloc[0], "North America")


class TestBuildDimCustomerProductWarehouse(unittest.TestCase):
    def setUp(self):
        self.dim_country = pd.DataFrame({"country_id": ["CTY001"], "country_key": [1]})

    def test_build_dim_customer_attaches_country_key(self):
        customers = pd.DataFrame({
            "customer_id": ["C1"], "country_id": ["CTY001"], "first_name": ["Jane"],
            "last_name": ["Doe"], "email": ["j@x.com"], "gender": ["Female"],
            "segment": ["Consumer"], "loyalty_tier": ["Gold"], "signup_date": ["2023-01-01"],
        })
        dim = sb.build_dim_customer(customers, self.dim_country)
        self.assertEqual(dim["customer_key"].iloc[0], 1)
        self.assertEqual(dim["country_key"].iloc[0], 1)

    def test_build_dim_product_assigns_sequential_keys(self):
        products = pd.DataFrame({
            "product_id": ["P1", "P2"], "product_name": ["A", "B"], "category": ["Tools", "Tools"],
            "sub_category": ["X", "Y"], "supplier_id": ["S1", "S1"],
            "unit_cost_usd": [5.0, 6.0], "unit_price_usd": [10.0, 12.0],
        })
        dim = sb.build_dim_product(products)
        self.assertEqual(list(dim["product_key"]), [1, 2])

    def test_build_dim_warehouse_attaches_country_key(self):
        warehouses = pd.DataFrame({
            "warehouse_id": ["WH1"], "warehouse_name": ["Main"], "warehouse_type": ["Fulfillment Center"],
            "country_id": ["CTY001"], "capacity_units": [5000000],
        })
        dim = sb.build_dim_warehouse(warehouses, self.dim_country)
        self.assertEqual(dim["warehouse_key"].iloc[0], 1)
        self.assertEqual(dim["country_key"].iloc[0], 1)


class TestBuildFactShipping(unittest.TestCase):
    def setUp(self):
        self.shipping = pd.DataFrame({
            "shipping_id": ["SHP1"], "order_id": ["ORD1"], "route_id": ["RT1"],
            "partner_id": ["LOG1"], "ship_date": ["2024-01-01"], "delivery_delay_days": [5],
            "shipping_status": ["Delivered"],
        })
        self.shipping_routes = pd.DataFrame({
            "route_id": ["RT1"], "origin_warehouse_id": ["WH1"],
            "destination_country_id": ["CTY001"], "standard_transit_days": [3],
        })
        self.dim_warehouse = pd.DataFrame({"warehouse_id": ["WH1"], "warehouse_key": [1]})
        self.dim_country = pd.DataFrame({"country_id": ["CTY001"], "country_key": [1]})

    def test_resolves_keys_and_renames_to_origin_destination(self):
        fact = sb.build_fact_shipping(self.shipping, self.shipping_routes, self.dim_warehouse, self.dim_country)
        self.assertEqual(fact["origin_warehouse_key"].iloc[0], 1)
        self.assertEqual(fact["destination_country_key"].iloc[0], 1)
        self.assertEqual(fact["date_key"].iloc[0], 20240101)

    def test_is_delayed_flag_respects_threshold(self):
        fact = sb.build_fact_shipping(self.shipping, self.shipping_routes, self.dim_warehouse,
                                       self.dim_country, delay_threshold_days=3)
        self.assertTrue(fact["is_delayed"].iloc[0])  # delay of 5 > threshold of 3

        on_time_shipping = self.shipping.copy()
        on_time_shipping["delivery_delay_days"] = 1
        fact2 = sb.build_fact_shipping(on_time_shipping, self.shipping_routes, self.dim_warehouse,
                                        self.dim_country, delay_threshold_days=3)
        self.assertFalse(fact2["is_delayed"].iloc[0])  # delay of 1 <= threshold of 3


class TestBuildFactReturns(unittest.TestCase):
    def test_carries_warehouse_and_country_from_the_original_order(self):
        returns = pd.DataFrame({
            "return_id": ["RET1"], "order_id": ["ORD1"], "order_item_id": ["OI1"],
            "return_date": ["2024-01-10"], "return_reason": ["Defective Product"],
            "return_status": ["Refunded"], "condition": ["Opened - Like New"],
            "refund_amount_usd": [15.0],
        })
        order_items = pd.DataFrame({"order_item_id": ["OI1"], "product_id": ["P1"]})
        orders = pd.DataFrame({
            "order_id": ["ORD1"], "customer_id": ["C1"], "warehouse_id": ["WH1"], "ship_country_id": ["CTY002"],
        })
        dim_product = pd.DataFrame({"product_id": ["P1"], "product_key": [1]})
        dim_customer = pd.DataFrame({"customer_id": ["C1"], "customer_key": [1]})
        dim_warehouse = pd.DataFrame({"warehouse_id": ["WH1"], "warehouse_key": [1], "country_key": [1]})
        dim_country = pd.DataFrame({"country_id": ["CTY001", "CTY002"], "country_key": [1, 2]})

        fact = sb.build_fact_returns(returns, order_items, orders, dim_product, dim_customer,
                                      dim_warehouse, dim_country)
        row = fact.iloc[0]
        self.assertEqual(row["warehouse_key"], 1)
        self.assertEqual(row["country_key"], 2)
        self.assertEqual(row["is_cross_border"], 1)  # warehouse country (1) != destination country (2)
        self.assertEqual(row["return_condition"], "Opened - Like New")  # renamed from "condition"


class TestBuildFactSales(unittest.TestCase):
    def setUp(self):
        self.orders = pd.DataFrame({
            "order_id": ["ORD1"], "order_date": ["2024-01-01"], "customer_id": ["C1"],
            "warehouse_id": ["WH1"], "ship_country_id": ["CTY002"], "order_status": ["Delivered"],
            "discount_pct": [0.10], "subtotal_usd": [100.0], "shipping_cost_usd": [10.0],
        })
        self.order_items = pd.DataFrame({
            "order_item_id": ["OI1", "OI2"], "order_id": ["ORD1", "ORD1"], "product_id": ["P1", "P2"],
            "quantity": [1, 1], "unit_price_usd": [60.0, 40.0], "line_discount_pct": [0.0, 0.0],
            "line_total_usd": [60.0, 40.0],  # 60% / 40% share of the order subtotal
        })
        self.dim_customer = pd.DataFrame({"customer_id": ["C1"], "customer_key": [1]})
        self.dim_product = pd.DataFrame({
            "product_id": ["P1", "P2"], "product_key": [1, 2], "unit_cost_usd": [20.0, 15.0],
        })
        # Warehouse is in country_key=1 (CTY001); order ships to CTY002 -> cross-border.
        self.dim_warehouse = pd.DataFrame({"warehouse_id": ["WH1"], "warehouse_key": [1], "country_key": [1]})
        self.dim_country = pd.DataFrame({"country_id": ["CTY001", "CTY002"], "country_key": [1, 2]})

    def test_shipping_cost_allocated_proportionally_and_reconciles(self):
        fact = sb.build_fact_sales(self.orders, self.order_items, self.dim_customer,
                                    self.dim_product, self.dim_warehouse, self.dim_country)
        # order_shipping_cost_usd=10, split 60/40 by each line's share of subtotal_usd=100
        line1 = fact[fact["order_item_id"] == "OI1"].iloc[0]
        line2 = fact[fact["order_item_id"] == "OI2"].iloc[0]
        self.assertAlmostEqual(line1["line_shipping_cost_usd"], 6.0)
        self.assertAlmostEqual(line2["line_shipping_cost_usd"], 4.0)
        self.assertAlmostEqual(fact["line_shipping_cost_usd"].sum(), 10.0)  # reconciles with the order total

    def test_order_level_discount_is_allocated_to_every_line(self):
        fact = sb.build_fact_sales(self.orders, self.order_items, self.dim_customer,
                                    self.dim_product, self.dim_warehouse, self.dim_country)
        line1 = fact[fact["order_item_id"] == "OI1"].iloc[0]
        # 60 * (1 - 0.10) = 54
        self.assertAlmostEqual(line1["line_net_revenue_usd"], 54.0)

    def test_cross_border_flag_true_when_warehouse_and_destination_countries_differ(self):
        fact = sb.build_fact_sales(self.orders, self.order_items, self.dim_customer,
                                    self.dim_product, self.dim_warehouse, self.dim_country)
        self.assertTrue((fact["is_cross_border"] == 1).all())

    def test_cross_border_flag_false_when_same_country(self):
        orders = self.orders.copy()
        orders["ship_country_id"] = "CTY001"  # same as the warehouse's country now
        fact = sb.build_fact_sales(orders, self.order_items, self.dim_customer,
                                    self.dim_product, self.dim_warehouse, self.dim_country)
        self.assertTrue((fact["is_cross_border"] == 0).all())

    def test_row_with_unmatched_product_is_dropped_not_crashed(self):
        order_items = pd.concat([self.order_items, pd.DataFrame({
            "order_item_id": ["OI3"], "order_id": ["ORD1"], "product_id": ["P_UNKNOWN"],
            "quantity": [1], "unit_price_usd": [10.0], "line_discount_pct": [0.0], "line_total_usd": [10.0],
        })], ignore_index=True)
        fact = sb.build_fact_sales(self.orders, order_items, self.dim_customer,
                                    self.dim_product, self.dim_warehouse, self.dim_country)
        self.assertNotIn("OI3", fact["order_item_id"].values)  # dropped via dropna, no exception raised
        self.assertEqual(len(fact), 2)


if __name__ == "__main__":
    unittest.main()
