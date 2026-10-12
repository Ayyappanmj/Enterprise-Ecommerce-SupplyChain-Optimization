import numpy as np
import pandas as pd


def random_dates(rng, start, end, n):
    """Vectorized random dates between start and end (inclusive), returned as pandas Timestamps."""
    start_u = pd.Timestamp(start).value // 10**9
    end_u = pd.Timestamp(end).value // 10**9
    secs = rng.integers(start_u, end_u, size=n)
    return pd.to_datetime(secs, unit="s")


def zero_pad_id(prefix, numbers, width=8):
    return [f"{prefix}{n:0{width}d}" for n in numbers]
