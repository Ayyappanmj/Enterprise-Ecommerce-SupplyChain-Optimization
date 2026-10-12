"""
Central configuration for enterprise data generation.

Change SCALE to "full" for the production-size dataset described in the
project spec, or "sample" for a fast, small dataset useful while developing
downstream ETL / cleaning / SQL code.
"""
import os

SCALE = os.environ.get("DATA_SCALE", "full")  # "full" or "sample"
SEED = 42

_FULL = dict(
    n_regions=5,
    n_countries=30,
    n_customers=50_000,
    n_suppliers=2_000,
    n_products=10_000,
    n_warehouses=150,
    n_logistics_partners=100,
    n_shipping_routes=300,
    n_orders=500_000,
    n_returns=75_000,
    n_campaigns=500,
    n_inventory_records=300_000,
    exchange_rate_days=1_100,  # covers the full 2023-01-01..2025-12-31 order date range
)

_SAMPLE = dict(
    n_regions=5,
    n_countries=15,
    n_customers=2_000,
    n_suppliers=200,
    n_products=800,
    n_warehouses=25,
    n_logistics_partners=20,
    n_shipping_routes=60,
    n_orders=10_000,
    n_returns=1_500,
    n_campaigns=50,
    n_inventory_records=8_000,
    exchange_rate_days=1_100,
)

CFG = _FULL if SCALE == "full" else _SAMPLE

# Output directory for raw generated CSVs
RAW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "raw",
)
os.makedirs(RAW_DIR, exist_ok=True)

ORDER_DATE_START = "2023-01-01"
ORDER_DATE_END = "2025-12-31"
