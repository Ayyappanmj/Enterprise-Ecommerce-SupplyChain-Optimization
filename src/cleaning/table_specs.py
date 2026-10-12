"""
Declares WHAT to clean per table; cleaning_engine.py declares HOW. Keeping
these separate means adding a new table to the pipeline is a config entry,
not new code.
"""

TABLE_SPECS = {
    "regions": {"primary_key": ["region_id"], "null_critical": ["region_id", "region_name"]},
    "countries": {"primary_key": ["country_id"], "null_critical": ["country_id", "country_name", "currency_code"]},
    "currencies": {"primary_key": ["currency_code"], "null_critical": ["currency_code"]},
    "exchange_rates": {"primary_key": ["date", "currency_code"], "null_critical": ["date", "currency_code", "rate_to_usd"]},

    "customers": {
        "primary_key": ["customer_id"],
        "null_critical": ["customer_id", "country_id"],
    },
    "suppliers": {
        "primary_key": ["supplier_id"],
        "null_critical": ["supplier_id", "country_id"],
        "outlier_cols": ["rating"],
    },
    "products": {
        "primary_key": ["product_id"],
        "null_critical": ["product_id", "supplier_id"],
        "negative_check_cols": ["unit_cost_usd", "unit_price_usd", "weight_kg"],
        "outlier_cols": ["unit_price_usd", "unit_cost_usd"],
    },
    "warehouses": {"primary_key": ["warehouse_id"], "null_critical": ["warehouse_id", "country_id"]},
    "logistics_partners": {"primary_key": ["partner_id"], "null_critical": ["partner_id"]},
    "shipping_routes": {
        "primary_key": ["route_id"],
        "null_critical": ["route_id", "origin_warehouse_id", "destination_country_id"],
        "negative_check_cols": ["standard_transit_days"],
    },

    "orders": {
        "primary_key": ["order_id"],
        "null_critical": ["order_id", "customer_id", "order_date"],
        "negative_check_cols": ["subtotal_usd", "shipping_cost_usd", "tax_amount_usd", "total_amount_usd"],
        "outlier_cols": ["total_amount_usd", "shipping_cost_usd"],
        "timezone": {"date_cols": ["order_date"], "country_col": "ship_country_id"},
        "currency_convert": {
            "usd_col": "total_amount_usd", "currency_col": "currency_code",
            "date_col": "order_date", "out_col": "total_amount_local",
        },
    },
    "order_items": {
        "primary_key": ["order_item_id"],
        "null_critical": ["order_item_id", "order_id", "product_id"],
        "negative_check_cols": ["quantity", "unit_price_usd", "line_total_usd"],
        "outlier_cols": ["line_total_usd"],
    },
    "inventory": {
        "primary_key": ["inventory_id"],
        "null_critical": ["inventory_id", "warehouse_id", "product_id"],
        "negative_check_cols": ["stock_quantity", "reorder_level"],
    },
    "shipping": {
        "primary_key": ["shipping_id"],
        "null_critical": ["shipping_id", "order_id", "ship_date"],
        "impossible_date_pairs": [("ship_date", "promised_delivery_date"), ("ship_date", "actual_delivery_date")],
        "outlier_cols": ["delivery_delay_days"],
    },
    "returns": {
        "primary_key": ["return_id"],
        "null_critical": ["return_id", "order_id"],
        "negative_check_cols": ["refund_amount_usd"],
        "outlier_cols": ["refund_amount_usd"],
    },
    "payments": {
        "primary_key": ["payment_id"],
        "null_critical": ["payment_id", "order_id"],
        "negative_check_cols": ["amount_usd"],
        "outlier_cols": ["amount_usd"],
    },
    "marketing_campaigns": {
        "primary_key": ["campaign_id"],
        "null_critical": ["campaign_id"],
        "negative_check_cols": ["budget_usd"],
        "outlier_cols": ["budget_usd"],
    },
}
