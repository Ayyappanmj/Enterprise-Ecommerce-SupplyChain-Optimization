"""
Loads the star schema into a real MySQL 8.0+ server: runs sql/schema.sql to
create the tables, then bulk-loads each DataFrame with SQLAlchemy + pandas
.to_sql(). Requires `pip install sqlalchemy pymysql`.

The import of sqlalchemy/pymysql is deferred to load() (not module level) so
the rest of this codebase works fine without them installed - the same
pattern used for the GCS/S3 uploaders in Phase 3.
"""
import os

from .config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    SQL_DIR, LOAD_CHUNK_SIZE,
)
from src.utils.logging_setup import get_logger

logger = get_logger("warehouse.mysql")

LOAD_ORDER = ["DimDate", "DimCountry", "DimCustomer", "DimProduct", "DimWarehouse",
              "FactSales", "FactShipping", "FactReturns"]


def _get_engine():
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise ImportError(
            "sqlalchemy is not installed. Run: pip install sqlalchemy pymysql --break-system-packages"
        ) from exc

    url = (f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
           f"{MYSQL_DATABASE}?charset=utf8mb4")
    return create_engine(url, pool_pre_ping=True)


def create_schema() -> None:
    """Runs sql/schema.sql against the target MySQL server (creates the
    database if needed, drops/recreates all 8 tables)."""
    engine = _get_engine()
    schema_path = os.path.join(SQL_DIR, "schema.sql")
    with open(schema_path) as f:
        script = f.read()

    # MySQL's DBAPI drivers generally don't support multi-statement scripts
    # in one execute() call, so split on ';' (schema.sql has no ';' inside
    # string literals/comments that would make this unsafe).
    statements = [s.strip() for s in script.split(";") if s.strip() and not s.strip().startswith("--")]

    with engine.begin() as conn:
        from sqlalchemy import text
        for stmt in statements:
            conn.execute(text(stmt))
    logger.info(f"Applied {schema_path} to {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")


def load(tables: dict) -> None:
    engine = _get_engine()
    for table_name in LOAD_ORDER:
        df = tables.get(table_name)
        if df is None:
            continue
        df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=LOAD_CHUNK_SIZE, method="multi")
        logger.info(f"Loaded {len(df):,} row(s) into {table_name}")


def verify() -> dict:
    engine = _get_engine()
    from sqlalchemy import text
    with engine.connect() as conn:
        counts = {
            t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            for t in LOAD_ORDER
        }
        top_country = conn.execute(text("""
            SELECT c.country_name, ROUND(SUM(fs.line_gross_profit_usd), 2) AS gross_profit
            FROM FactSales fs JOIN DimCountry c ON fs.country_key = c.country_key
            GROUP BY c.country_name ORDER BY gross_profit DESC LIMIT 1
        """)).fetchone()
    return {"row_counts": counts, "top_country_by_gross_profit": tuple(top_country) if top_country else None}
