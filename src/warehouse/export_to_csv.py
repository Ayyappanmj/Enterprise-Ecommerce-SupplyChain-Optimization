"""
Exports every table in the SQLite warehouse to CSV, for Power BI's
Get Data > Text/CSV (no MySQL server, no ODBC driver required - the
fastest path to a working Phase 8 dashboard).

Usage:
    python -m src.warehouse.export_to_csv
"""
import os
import sqlite3

import pandas as pd

from .config import SQLITE_PATH, WAREHOUSE_DIR

OUT_DIR = os.path.join(WAREHOUSE_DIR, "csv_export")
TABLES = ["DimDate", "DimCountry", "DimCustomer", "DimProduct", "DimWarehouse",
          "FactSales", "FactShipping", "FactReturns"]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    for table in TABLES:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        out_path = os.path.join(OUT_DIR, f"{table}.csv")
        df.to_csv(out_path, index=False)
        print(f"{table}: {len(df):,} rows -> {out_path}")
    conn.close()
    print(f"\nDone. In Power BI Desktop: Get Data > Folder > {OUT_DIR}")


if __name__ == "__main__":
    main()
