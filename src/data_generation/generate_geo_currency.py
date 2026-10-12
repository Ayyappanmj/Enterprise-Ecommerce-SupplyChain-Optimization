"""Phase 1: Regions, Countries, Currencies, Exchange_Rates."""
import numpy as np
import pandas as pd
import os

from . import reference_data as ref
from .config import CFG, RAW_DIR, SEED, ORDER_DATE_START, ORDER_DATE_END
from .utils import zero_pad_id


def generate():
    rng = np.random.default_rng(SEED)

    # --- Regions ---
    regions = ref.REGIONS[: CFG["n_regions"]]
    df_regions = pd.DataFrame({
        "region_id": zero_pad_id("REG", range(1, len(regions) + 1), 2),
        "region_name": regions,
    })
    region_id_map = dict(zip(df_regions["region_name"], df_regions["region_id"]))

    # --- Countries ---
    countries = ref.COUNTRIES[: CFG["n_countries"]]
    df_countries = pd.DataFrame(countries, columns=["country_name", "region_name", "currency_code"])
    df_countries.insert(0, "country_id", zero_pad_id("CTY", range(1, len(df_countries) + 1), 3))
    df_countries["region_id"] = df_countries["region_name"].map(region_id_map)
    df_countries = df_countries[["country_id", "country_name", "region_id", "currency_code"]]

    # --- Currencies ---
    used_currencies = sorted(df_countries["currency_code"].unique())
    df_currencies = pd.DataFrame([
        {"currency_code": c, "currency_name": ref.CURRENCIES[c][0], "symbol": ref.CURRENCIES[c][1]}
        for c in used_currencies
    ])

    # --- Exchange Rates (daily, vs USD) ---
    n_days = CFG["exchange_rate_days"]
    dates = pd.date_range(end=ORDER_DATE_END, periods=n_days, freq="D")
    rows = []
    for c in used_currencies:
        base = ref.BASE_RATE_TO_USD[c]
        noise = rng.normal(0, 0.01, size=n_days).cumsum()
        rates = base * (1 + noise)
        rows.append(pd.DataFrame({
            "date": dates,
            "currency_code": c,
            "rate_to_usd": np.round(rates, 8),
        }))
    df_fx = pd.concat(rows, ignore_index=True)

    df_regions.to_csv(os.path.join(RAW_DIR, "regions.csv"), index=False)
    df_countries.to_csv(os.path.join(RAW_DIR, "countries.csv"), index=False)
    df_currencies.to_csv(os.path.join(RAW_DIR, "currencies.csv"), index=False)
    df_fx.to_csv(os.path.join(RAW_DIR, "exchange_rates.csv"), index=False)

    print(f"regions: {len(df_regions)}, countries: {len(df_countries)}, "
          f"currencies: {len(df_currencies)}, exchange_rates: {len(df_fx)}")
    return df_regions, df_countries, df_currencies, df_fx


if __name__ == "__main__":
    generate()
