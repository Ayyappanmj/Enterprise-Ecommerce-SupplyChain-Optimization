"""Phase 1: Warehouses, Logistics_Partners, Shipping_Routes."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED
from .utils import zero_pad_id


def generate_warehouses(df_countries):
    rng = np.random.default_rng(SEED + 4)
    n = CFG["n_warehouses"]
    countries = df_countries.sample(n, replace=True, random_state=SEED + 4).reset_index(drop=True)
    df = pd.DataFrame({
        "warehouse_id": zero_pad_id("WH", range(1, n + 1), 4),
        "warehouse_name": [
            f"{rng.choice(ref.CITIES_BY_COUNTRY.get(c, [c]))} {t}"
            for c, t in zip(countries["country_name"], rng.choice(ref.WAREHOUSE_TYPES, size=n))
        ],
        "country_id": countries["country_id"].values,
        "region_id": countries["region_id"].values,
        "warehouse_type": rng.choice(ref.WAREHOUSE_TYPES, size=n),
        # Capacity is sized to be comparable with the volume Phase 1 actually
        # generates (n_inventory_records spread over n_warehouses, each
        # holding up to a few thousand units per product line), so Phase 5's
        # utilization_pct comes out in a realistic range instead of
        # thousands of percent.
        "capacity_units": rng.integers(3_000_000, 12_000_000, size=n),
    })
    df.to_csv(os.path.join(RAW_DIR, "warehouses.csv"), index=False)
    print(f"warehouses: {len(df)}")
    return df


def generate_logistics_partners(df_countries):
    rng = np.random.default_rng(SEED + 5)
    n = CFG["n_logistics_partners"]
    hq = df_countries.sample(n, replace=True, random_state=SEED + 5).reset_index(drop=True)
    partner_words = ["Global", "Rapid", "Prime", "Transworld", "Swift", "Continental", "Apex", "United"]
    partner_suffix = ["Logistics", "Freight", "Cargo", "Express", "Shipping Co."]
    df = pd.DataFrame({
        "partner_id": zero_pad_id("LOG", range(1, n + 1), 4),
        "partner_name": [f"{rng.choice(partner_words)} {rng.choice(partner_suffix)} {i}" for i in range(n)],
        "hq_country_id": hq["country_id"].values,
        "service_level": rng.choice(ref.SERVICE_LEVELS, size=n),
        "avg_rating": np.round(rng.uniform(2.8, 4.9, size=n), 1),
    })
    df.to_csv(os.path.join(RAW_DIR, "logistics_partners.csv"), index=False)
    print(f"logistics_partners: {len(df)}")
    return df


def generate_shipping_routes(df_warehouses, df_countries, df_partners):
    rng = np.random.default_rng(SEED + 6)
    n = CFG["n_shipping_routes"]
    origin_wh = df_warehouses["warehouse_id"].sample(n, replace=True, random_state=SEED + 6).values
    dest_country = df_countries["country_id"].sample(n, replace=True, random_state=SEED + 7).values
    partner = df_partners["partner_id"].sample(n, replace=True, random_state=SEED + 8).values
    route_type = rng.choice(ref.ROUTE_TYPES, size=n, p=[0.25, 0.35, 0.30, 0.10])
    transit_days = np.select(
        [route_type == "Air", route_type == "Sea", route_type == "Ground", route_type == "Rail"],
        [rng.integers(1, 5, size=n), rng.integers(15, 45, size=n),
         rng.integers(2, 10, size=n), rng.integers(5, 20, size=n)],
    )
    df = pd.DataFrame({
        "route_id": zero_pad_id("RT", range(1, n + 1), 4),
        "origin_warehouse_id": origin_wh,
        "destination_country_id": dest_country,
        "partner_id": partner,
        "route_type": route_type,
        "standard_transit_days": transit_days,
    })
    df.to_csv(os.path.join(RAW_DIR, "shipping_routes.csv"), index=False)
    print(f"shipping_routes: {len(df)}")
    return df


if __name__ == "__main__":
    from .generate_geo_currency import generate as gen_geo
    _, df_countries, _, _ = gen_geo()
    df_wh = generate_warehouses(df_countries)
    df_part = generate_logistics_partners(df_countries)
    generate_shipping_routes(df_wh, df_countries, df_part)
