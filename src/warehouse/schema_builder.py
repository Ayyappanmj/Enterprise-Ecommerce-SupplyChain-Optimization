"""
Builds the star schema's dimension and fact tables as plain DataFrames with
surrogate integer keys, using nothing but pandas/NumPy - so this logic (the
actual dimensional modeling: grain, keys, joins) can be fully tested without
any database driver at all. sqlite_loader.py and mysql_loader.py just persist
whatever this module produces.
"""
import numpy as np
import pandas as pd


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    dates = pd.to_datetime(dates.dropna()).dt.normalize()
    full_range = pd.date_range(dates.min(), dates.max(), freq="D")
    df = pd.DataFrame({"full_date": full_range})
    df["date_key"] = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["full_date"].dt.year
    df["quarter"] = df["full_date"].dt.quarter
    df["month"] = df["full_date"].dt.month
    df["month_name"] = df["full_date"].dt.month_name()
    df["day"] = df["full_date"].dt.day
    df["day_of_week"] = df["full_date"].dt.dayofweek
    df["day_name"] = df["full_date"].dt.day_name()
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    return df[["date_key", "full_date", "year", "quarter", "month", "month_name",
               "day", "day_of_week", "day_name", "is_weekend"]]


def date_to_key(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y%m%d").astype(int)


def build_dim_country(countries: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    df = countries.merge(regions[["region_id", "region_name"]], on="region_id", how="left")
    df = df.reset_index(drop=True)
    df.insert(0, "country_key", np.arange(1, len(df) + 1))
    return df[["country_key", "country_id", "country_name", "region_name", "currency_code"]]


def build_dim_customer(customers: pd.DataFrame, dim_country: pd.DataFrame) -> pd.DataFrame:
    df = customers.merge(dim_country[["country_id", "country_key"]], on="country_id", how="left")
    df = df.reset_index(drop=True)
    df.insert(0, "customer_key", np.arange(1, len(df) + 1))
    cols = ["customer_key", "customer_id", "first_name", "last_name", "email", "gender",
            "segment", "loyalty_tier", "country_key", "signup_date"]
    return df[[c for c in cols if c in df.columns]]


def build_dim_product(products: pd.DataFrame) -> pd.DataFrame:
    df = products.reset_index(drop=True).copy()
    df.insert(0, "product_key", np.arange(1, len(df) + 1))
    cols = ["product_key", "product_id", "product_name", "category", "sub_category",
            "supplier_id", "unit_cost_usd", "unit_price_usd"]
    return df[[c for c in cols if c in df.columns]]


def build_dim_warehouse(warehouses: pd.DataFrame, dim_country: pd.DataFrame) -> pd.DataFrame:
    df = warehouses.merge(dim_country[["country_id", "country_key"]], on="country_id", how="left")
    df = df.reset_index(drop=True)
    df.insert(0, "warehouse_key", np.arange(1, len(df) + 1))
    cols = ["warehouse_key", "warehouse_id", "warehouse_name", "warehouse_type",
            "country_key", "capacity_units"]
    return df[[c for c in cols if c in df.columns]]


def build_fact_sales(orders: pd.DataFrame, order_items: pd.DataFrame,
                      dim_customer: pd.DataFrame, dim_product: pd.DataFrame,
                      dim_warehouse: pd.DataFrame, dim_country: pd.DataFrame) -> pd.DataFrame:
    fact = order_items.merge(
        orders[["order_id", "order_date", "customer_id", "warehouse_id", "ship_country_id",
                "order_status", "discount_pct", "subtotal_usd", "shipping_cost_usd"]
               ].rename(columns={"discount_pct": "order_discount_pct",
                                 "shipping_cost_usd": "order_shipping_cost_usd"}),
        on="order_id", how="inner",
    )
    fact = fact.merge(dim_product[["product_id", "product_key", "unit_cost_usd"]], on="product_id", how="left")
    fact = fact.merge(dim_customer[["customer_id", "customer_key"]], on="customer_id", how="left")
    fact = fact.merge(
        dim_warehouse[["warehouse_id", "warehouse_key", "country_key"]].rename(
            columns={"country_key": "warehouse_country_key"}),
        on="warehouse_id", how="left",
    )
    fact = fact.merge(
        dim_country[["country_id", "country_key"]], left_on="ship_country_id", right_on="country_id", how="left"
    )

    fact["date_key"] = date_to_key(fact["order_date"])
    # An order is "cross-border" when it ships from a warehouse in a different
    # country than its destination (the project's core cost driver).
    fact["is_cross_border"] = (fact["warehouse_country_key"] != fact["country_key"]).astype(int)
    # The order's shipping cost is allocated to each line in proportion to the
    # line's share of the order subtotal, so SUM over FactSales reconciles with
    # the order-grain shipping cost (verified against Phase 5 in the README).
    fact["line_shipping_cost_usd"] = np.round(
        np.where(fact["subtotal_usd"] > 0,
                 fact["order_shipping_cost_usd"] * fact["line_total_usd"] / fact["subtotal_usd"], 0.0), 2)
    fact["line_cost_usd"] = np.round(fact["quantity"] * fact["unit_cost_usd"], 2)
    # line_total_usd only reflects the item-level discount; the order-level
    # discount (orders.discount_pct) applies uniformly across every line in
    # the order and must be allocated here too, or FactSales overstates
    # revenue/profit relative to the order-grain figures in Phase 5's
    # order_features (verified: this allocation is what makes SUM(FactSales
    # line_net_revenue_usd) reconcile exactly with SUM(order_features
    # product_revenue_usd)).
    fact["line_net_revenue_usd"] = np.round(fact["line_total_usd"] * (1 - fact["order_discount_pct"]), 2)
    fact["line_gross_profit_usd"] = np.round(fact["line_net_revenue_usd"] - fact["line_cost_usd"], 2)

    cols = ["date_key", "order_id", "order_item_id", "customer_key", "product_key",
            "warehouse_key", "country_key", "order_status", "quantity", "unit_price_usd",
            "unit_cost_usd", "line_discount_pct", "order_discount_pct", "line_total_usd",
            "line_net_revenue_usd", "line_cost_usd", "line_gross_profit_usd",
            "line_shipping_cost_usd", "is_cross_border"]
    out = fact[cols].dropna(subset=["customer_key", "product_key", "warehouse_key", "country_key"])
    for k in ["customer_key", "product_key", "warehouse_key", "country_key"]:
        out[k] = out[k].astype(int)
    return out.reset_index(drop=True)


def build_fact_shipping(shipping: pd.DataFrame, shipping_routes: pd.DataFrame,
                         dim_warehouse: pd.DataFrame, dim_country: pd.DataFrame,
                         delay_threshold_days: int = 3) -> pd.DataFrame:
    fact = shipping.merge(
        shipping_routes[["route_id", "origin_warehouse_id", "destination_country_id", "standard_transit_days"]],
        on="route_id", how="left",
    )
    fact = fact.merge(
        dim_warehouse[["warehouse_id", "warehouse_key"]],
        left_on="origin_warehouse_id", right_on="warehouse_id", how="left",
    )
    fact = fact.merge(
        dim_country[["country_id", "country_key"]],
        left_on="destination_country_id", right_on="country_id", how="left",
    )

    fact["date_key"] = date_to_key(fact["ship_date"])
    fact["is_delayed"] = fact["delivery_delay_days"] > delay_threshold_days

    cols = ["date_key", "shipping_id", "order_id", "warehouse_key", "country_key",
            "partner_id", "route_id", "standard_transit_days", "delivery_delay_days",
            "is_delayed", "shipping_status"]
    out = fact[cols].dropna(subset=["warehouse_key", "country_key"])
    for k in ["warehouse_key", "country_key"]:
        out[k] = out[k].astype(int)
    return out.rename(columns={"warehouse_key": "origin_warehouse_key",
                                "country_key": "destination_country_key"}).reset_index(drop=True)


def build_fact_returns(returns: pd.DataFrame, order_items: pd.DataFrame, orders: pd.DataFrame,
                        dim_product: pd.DataFrame, dim_customer: pd.DataFrame,
                        dim_warehouse: pd.DataFrame, dim_country: pd.DataFrame) -> pd.DataFrame:
    """warehouse_key / country_key / is_cross_border are carried from the
    original order, so returns can be sliced by the same Country and Warehouse
    dimensions as sales without an ambiguous many-to-many relationship in BI."""
    fact = returns.merge(order_items[["order_item_id", "product_id"]], on="order_item_id", how="left")
    fact = fact.merge(orders[["order_id", "customer_id", "warehouse_id", "ship_country_id"]],
                      on="order_id", how="left")
    fact = fact.merge(
        dim_warehouse[["warehouse_id", "warehouse_key", "country_key"]].rename(
            columns={"country_key": "warehouse_country_key"}),
        on="warehouse_id", how="left",
    )
    fact = fact.merge(dim_country[["country_id", "country_key"]],
                      left_on="ship_country_id", right_on="country_id", how="left")
    fact["is_cross_border"] = (fact["warehouse_country_key"] != fact["country_key"]).astype(int)
    fact = fact.merge(dim_product[["product_id", "product_key"]], on="product_id", how="left")
    fact = fact.merge(dim_customer[["customer_id", "customer_key"]], on="customer_id", how="left")

    fact["date_key"] = date_to_key(fact["return_date"])
    fact = fact.rename(columns={"condition": "return_condition"})

    cols = ["date_key", "return_id", "order_id", "product_key", "customer_key",
            "warehouse_key", "country_key", "return_reason", "return_status",
            "return_condition", "refund_amount_usd", "is_cross_border"]
    out = fact[cols].dropna(subset=["product_key", "customer_key", "warehouse_key", "country_key"])
    for k in ["product_key", "customer_key", "warehouse_key", "country_key"]:
        out[k] = out[k].astype(int)
    return out.reset_index(drop=True)
