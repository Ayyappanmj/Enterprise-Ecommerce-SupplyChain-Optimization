import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLEANED_DIR = os.path.join(ROOT_DIR, "data", "processed", "cleaned")
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "processed", "features")
WAREHOUSE_DIR = os.path.join(ROOT_DIR, "data", "warehouse")
SQL_DIR = os.path.join(ROOT_DIR, "sql")

os.makedirs(WAREHOUSE_DIR, exist_ok=True)

# ENGINE = "mysql" (real MySQL 8.0+, via SQLAlchemy + PyMySQL) or
#          "sqlite" (zero-dependency local file DB, stdlib only - what this
#          repo was built and tested against; see README Phase 6 caveat)
WAREHOUSE_ENGINE = os.environ.get("WAREHOUSE_ENGINE", "sqlite").lower()

SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(WAREHOUSE_DIR, "warehouse.db"))

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "ecommerce_supply_chain")

LOAD_CHUNK_SIZE = 10_000
