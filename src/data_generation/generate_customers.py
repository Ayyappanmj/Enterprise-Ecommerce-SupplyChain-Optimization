"""Phase 1: Customers."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED, ORDER_DATE_START, ORDER_DATE_END
from .utils import zero_pad_id, random_dates


def generate(df_countries):
    rng = np.random.default_rng(SEED + 1)
    n = CFG["n_customers"]

    first = rng.choice(ref.FIRST_NAMES, size=n)
    last = rng.choice(ref.LAST_NAMES, size=n)
    countries = df_countries["country_name"].sample(n, replace=True, random_state=SEED + 1).values
    cities = np.array([rng.choice(ref.CITIES_BY_COUNTRY.get(c, [c])) for c in countries])

    birth_dates = random_dates(rng, "1955-01-01", "2005-12-31", n)
    signup_dates = random_dates(rng, ORDER_DATE_START, ORDER_DATE_END, n)

    df = pd.DataFrame({
        "customer_id": zero_pad_id("CUST", range(1, n + 1), 7),
        "first_name": first,
        "last_name": last,
        "email": [f"{f.lower()}.{l.lower()}{i}@example.com" for i, (f, l) in enumerate(zip(first, last))],
        "gender": rng.choice(["Male", "Female", "Other"], size=n, p=[0.48, 0.48, 0.04]),
        "birth_date": birth_dates.date,
        "signup_date": signup_dates,
        "country_name": countries,
        "city": cities,
        "segment": rng.choice(ref.CUSTOMER_SEGMENTS, size=n, p=[0.7, 0.2, 0.1]),
        "loyalty_tier": rng.choice(ref.LOYALTY_TIERS, size=n, p=[0.5, 0.3, 0.15, 0.05]),
    })
    df = df.merge(df_countries[["country_id", "country_name"]], on="country_name", how="left")
    df = df.drop(columns=["country_name"])
    cols = ["customer_id", "first_name", "last_name", "email", "gender", "birth_date",
            "signup_date", "country_id", "city", "segment", "loyalty_tier"]
    df = df[cols]

    df.to_csv(os.path.join(RAW_DIR, "customers.csv"), index=False)
    print(f"customers: {len(df)}")
    return df


if __name__ == "__main__":
    from .generate_geo_currency import generate as gen_geo
    _, df_countries, _, _ = gen_geo()
    generate(df_countries)
