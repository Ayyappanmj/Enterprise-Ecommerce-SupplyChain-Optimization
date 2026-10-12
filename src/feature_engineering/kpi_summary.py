import numpy as np
import pandas as pd

from .customer_features import overall_repeat_purchase_rate


def build(order_features: pd.DataFrame, customer_features: pd.DataFrame,
          shipping_features: pd.DataFrame) -> dict:
    total_revenue = float(order_features["product_revenue_usd"].sum())
    total_gross_profit = float(order_features["gross_profit_usd"].sum())
    total_net_profit = float(order_features["net_profit_usd"].sum())
    num_orders = int(len(order_features))
    num_returned = int(order_features["is_returned"].sum())

    return {
        "total_orders": num_orders,
        "total_product_revenue_usd": round(total_revenue, 2),
        "total_gross_profit_usd": round(total_gross_profit, 2),
        "overall_gross_margin_pct": round(total_gross_profit / total_revenue, 4) if total_revenue else None,
        "total_net_profit_usd": round(total_net_profit, 2),
        "overall_net_margin_pct": round(total_net_profit / total_revenue, 4) if total_revenue else None,
        "overall_average_order_value_usd": round(total_revenue / num_orders, 2) if num_orders else None,
        "overall_return_rate": round(num_returned / num_orders, 4) if num_orders else None,
        "repeat_purchase_rate": overall_repeat_purchase_rate(customer_features),
        "avg_delivery_delay_days": round(float(shipping_features["delivery_delay_days"].mean()), 2),
        "pct_shipments_delayed": round(float(shipping_features["is_delayed"].mean()), 4),
    }
