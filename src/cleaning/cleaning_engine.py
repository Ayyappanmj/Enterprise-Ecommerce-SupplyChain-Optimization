import pandas as pd

from . import cleaning_utils as cu
from src.utils.logging_setup import get_logger

logger = get_logger("cleaning.engine")


def clean_table(table_name: str, df: pd.DataFrame, spec: dict,
                 countries_df: pd.DataFrame = None, fx_df: pd.DataFrame = None) -> tuple:
    report = {"table": table_name, "rows_before": len(df)}

    df, n_dup = cu.drop_duplicates(df, spec.get("primary_key", []))
    report["duplicates_removed"] = n_dup

    df, n_null = cu.drop_null_critical(df, spec.get("null_critical", []))
    report["null_rows_dropped"] = n_null

    df, n_neg = cu.fix_negative_values(df, spec.get("negative_check_cols", []))
    report["negative_values_fixed"] = n_neg

    n_impossible = 0
    for start_col, end_col in spec.get("impossible_date_pairs", []):
        df, n = cu.fix_impossible_dates(df, start_col, end_col)
        n_impossible += n
    report["impossible_dates_fixed"] = n_impossible

    df, n_outliers = cu.flag_outliers_iqr(df, spec.get("outlier_cols", []))
    report["outliers_flagged"] = n_outliers

    if "timezone" in spec and countries_df is not None:
        tz = spec["timezone"]
        df = cu.normalize_to_utc(df, tz["date_cols"], tz["country_col"], countries_df)
        report["timezone_normalized_cols"] = ",".join(tz["date_cols"])
    else:
        report["timezone_normalized_cols"] = ""

    if "currency_convert" in spec and fx_df is not None:
        cc = spec["currency_convert"]
        df = cu.convert_amount_to_local_currency(
            df, cc["usd_col"], cc["currency_col"], cc["date_col"], fx_df, cc["out_col"]
        )
        report["currency_converted"] = True
    else:
        report["currency_converted"] = False

    report["rows_after"] = len(df)
    logger.info(
        f"[{table_name}] {report['rows_before']} -> {report['rows_after']} rows | "
        f"dupes={n_dup} nulls={n_null} negatives={n_neg} "
        f"impossible_dates={n_impossible} outliers_flagged={n_outliers}"
    )
    return df, report
