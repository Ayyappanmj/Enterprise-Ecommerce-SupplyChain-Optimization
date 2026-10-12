"""Phase 1: Suppliers, Products."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED
from .utils import zero_pad_id, random_dates


def generate_suppliers(df_countries):
    rng = np.random.default_rng(SEED + 2)
    n = CFG["n_suppliers"]
    countries = df_countries.sample(n, replace=True, random_state=SEED + 2).reset_index(drop=True)
    names = [
        f"{rng.choice(ref.CITIES_BY_COUNTRY.get(c, [c]))} {rng.choice(ref.SUPPLIER_NAME_SUFFIXES)}"
        for c in countries["country_name"]
    ]
    df = pd.DataFrame({
        "supplier_id": zero_pad_id("SUP", range(1, n + 1), 6),
        "supplier_name": names,
        "country_id": countries["country_id"].values,
        "contact_email": [f"contact{i}@{n.split()[0].lower()}supply.com" for i, n in enumerate(names)],
        "rating": np.round(rng.uniform(2.5, 5.0, size=n), 1),
    })
    df.to_csv(os.path.join(RAW_DIR, "suppliers.csv"), index=False)
    print(f"suppliers: {len(df)}")
    return df


def generate_products(df_suppliers):
    rng = np.random.default_rng(SEED + 3)
    n = CFG["n_products"]

    categories = list(ref.PRODUCT_CATEGORIES.keys())
    cat_choice = rng.choice(categories, size=n)
    subcat_choice = [rng.choice(ref.PRODUCT_CATEGORIES[c]) for c in cat_choice]
    suppliers = df_suppliers["supplier_id"].sample(n, replace=True, random_state=SEED + 3).values

    unit_cost = np.round(rng.gamma(shape=2.5, scale=20, size=n) + 3, 2)
    margin_pct = rng.uniform(0.15, 0.65, size=n)
    unit_price = np.round(unit_cost / (1 - margin_pct), 2)

    df = pd.DataFrame({
        "product_id": zero_pad_id("PROD", range(1, n + 1), 7),
        "product_name": [f"{sc} {pid}" for sc, pid in zip(subcat_choice, range(1, n + 1))],
        "category": cat_choice,
        "sub_category": subcat_choice,
        "supplier_id": suppliers,
        "unit_cost_usd": unit_cost,
        "unit_price_usd": unit_price,
        "weight_kg": np.round(rng.gamma(shape=1.5, scale=1.2, size=n) + 0.05, 2),
        "launch_date": random_dates(rng, "2018-01-01", "2025-06-30", n).date,
    })
    df.to_csv(os.path.join(RAW_DIR, "products.csv"), index=False)
    print(f"products: {len(df)}")
    return df


if __name__ == "__main__":
    from .generate_geo_currency import generate as gen_geo
    _, df_countries, _, _ = gen_geo()
    df_sup = generate_suppliers(df_countries)
    generate_products(df_sup)
