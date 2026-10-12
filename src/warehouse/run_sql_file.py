"""
Runs every statement in a .sql file against the SQLite warehouse and reports
per-statement status and timing. Useful for validating the Phase 7 SQL
(window_queries.sql, business_queries.sql) and for applying views.sql.

Usage:
    python -m src.warehouse.run_sql_file sql/views.sql
    python -m src.warehouse.run_sql_file sql/business_queries.sql --show 3
    python -m src.warehouse.run_sql_file sql/business_queries.sql --timeout 30

Not for sql/procedures.sql or sql/schema.sql - those are MySQL-only.
"""
import argparse
import sqlite3
import time

from .config import SQLITE_PATH


def split_statements(sql_text: str) -> list:
    body = "\n".join(l for l in sql_text.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def main():
    parser = argparse.ArgumentParser(description="Run a .sql file against the SQLite warehouse")
    parser.add_argument("sql_file")
    parser.add_argument("--show", type=int, default=0, help="print the first N result rows of each SELECT")
    parser.add_argument("--timeout", type=float, default=60, help="per-statement time limit (seconds)")
    args = parser.parse_args()

    with open(args.sql_file) as f:
        statements = split_statements(f.read())

    conn = sqlite3.connect(SQLITE_PATH)
    ok = failed = timed_out = 0
    for i, stmt in enumerate(statements, 1):
        t0 = time.time()
        conn.set_progress_handler(lambda: 1 if time.time() - t0 > args.timeout else 0, 100_000)
        label = " ".join(stmt.split())[:80]
        try:
            cur = conn.execute(stmt)
            rows = cur.fetchall() if cur.description else []
            conn.commit()
            ok += 1
            print(f"[{i:>3}] OK   {time.time() - t0:6.2f}s  {len(rows):>6} rows  {label}")
            for row in rows[: args.show]:
                print("        ", row)
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc):
                timed_out += 1
                print(f"[{i:>3}] TIMEOUT (> {args.timeout}s)  {label}")
            else:
                failed += 1
                print(f"[{i:>3}] FAIL {exc}  {label}")

    conn.close()
    print(f"\n{ok} ok, {timed_out} timed out, {failed} failed of {len(statements)} statements")


if __name__ == "__main__":
    main()
