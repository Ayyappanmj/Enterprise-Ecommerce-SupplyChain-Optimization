"""
Phase 4 - Data Cleaning.

Reads every table from data/raw/, applies its cleaning spec
(src/cleaning/table_specs.py) via the generic cleaning_engine, writes the
cleaned result to data/processed/cleaned/, and writes a before/after summary
to reports/.

Usage:
    python -m src.cleaning.run_cleaning
"""
import os
import time

import pandas as pd

from .config import RAW_DIR, CLEANED_DIR, REPORTS_DIR
from .table_specs import TABLE_SPECS
from .cleaning_engine import clean_table
from src.utils.logging_setup import get_logger

logger = get_logger("cleaning.run")


def main():
    t0 = time.time()
    logger.info(f"=== Data cleaning starting: {len(TABLE_SPECS)} tables ===")

    countries_df = pd.read_csv(os.path.join(RAW_DIR, "countries.csv"))
    fx_df = pd.read_csv(os.path.join(RAW_DIR, "exchange_rates.csv"))

    reports = []
    for table_name, spec in TABLE_SPECS.items():
        csv_path = os.path.join(RAW_DIR, f"{table_name}.csv")
        if not os.path.exists(csv_path):
            logger.warning(f"[{table_name}] source file not found, skipping: {csv_path}")
            continue

        df = pd.read_csv(csv_path)
        cleaned_df, report = clean_table(table_name, df, spec, countries_df=countries_df, fx_df=fx_df)

        out_path = os.path.join(CLEANED_DIR, f"{table_name}_clean.csv")
        cleaned_df.to_csv(out_path, index=False)
        reports.append(report)

    report_df = pd.DataFrame(reports)
    summary_path = os.path.join(REPORTS_DIR, "data_cleaning_summary.csv")
    report_df.to_csv(summary_path, index=False)

    _write_markdown_report(report_df)

    logger.info(f"=== Data cleaning complete in {time.time() - t0:.1f}s. "
                f"Cleaned tables -> {CLEANED_DIR}, report -> {summary_path} ===")
    print(report_df.to_string(index=False))


def _write_markdown_report(report_df: pd.DataFrame):
    totals = report_df[[
        "duplicates_removed", "null_rows_dropped", "negative_values_fixed",
        "impossible_dates_fixed", "outliers_flagged",
    ]].sum()

    lines = [
        "# Data Cleaning Report — Before / After",
        "",
        f"Tables processed: **{len(report_df)}**  |  "
        f"Total rows before: **{int(report_df['rows_before'].sum()):,}**  |  "
        f"Total rows after: **{int(report_df['rows_after'].sum()):,}**",
        "",
        "## Totals across all tables",
        "",
        f"- Duplicate rows removed: **{int(totals['duplicates_removed']):,}**",
        f"- Rows dropped for null primary/foreign keys: **{int(totals['null_rows_dropped']):,}**",
        f"- Negative values clipped to 0: **{int(totals['negative_values_fixed']):,}**",
        f"- Impossible dates corrected (end date nulled): **{int(totals['impossible_dates_fixed']):,}**",
        f"- Statistical outliers flagged (kept, not deleted): **{int(totals['outliers_flagged']):,}**",
        "",
        "## Per-table detail",
        "",
        "| Table | Before | After | Dupes | Nulls Dropped | Negatives Fixed | "
        "Impossible Dates | Outliers Flagged | TZ Normalized | Currency Converted |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in report_df.iterrows():
        lines.append(
            f"| {r['table']} | {r['rows_before']:,} | {r['rows_after']:,} | {r['duplicates_removed']} | "
            f"{r['null_rows_dropped']} | {r['negative_values_fixed']} | {r['impossible_dates_fixed']} | "
            f"{r['outliers_flagged']} | {r['timezone_normalized_cols'] or '—'} | "
            f"{'Yes' if r['currency_converted'] else '—'} |"
        )
    lines += [
        "",
        "## Methodology notes",
        "",
        "- **Duplicate removal**: exact duplicates on each table's primary key, first occurrence kept.",
        "- **Null handling**: rows missing a primary key or a required foreign key are dropped "
        "(they can never join correctly downstream); non-critical nulls are left as-is for now.",
        "- **Negative quantity/amount detection**: quantities, prices, costs and stock levels can "
        "never legitimately be negative; such values are clipped to 0 and counted.",
        "- **Impossible shipping dates**: any `actual_delivery_date` or `promised_delivery_date` "
        "earlier than its `ship_date` is nulled out (delivery treated as unconfirmed) rather than "
        "dropping the whole shipment record.",
        "- **Outlier detection**: Tukey's IQR method (1.5x IQR fences) per numeric column of interest. "
        "Outliers are **flagged** in a `<column>_is_outlier` column, not deleted - unusually large "
        "orders, refunds, or delays are exactly the signal a margin/delay investigation cares about.",
        "- **Timezone normalization**: `orders.order_date` is treated as local time at the shipping "
        "country and converted to UTC (`order_date_utc`) using an approximate standard-time offset "
        "per country, so cross-region time-based analysis isn't skewed by local clocks.",
        "- **Currency conversion**: `orders.total_amount_usd` is converted back to the order's local "
        "currency (`total_amount_local`) using the historical daily FX rate closest to (on or before) "
        "the order date, demonstrating an as-of currency join.",
    ]

    with open(os.path.join(REPORTS_DIR, "data_cleaning_report.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
