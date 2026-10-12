"""
Configuration for Phase 3 (Cloud Storage).

Everything is driven by environment variables so the same code runs against
GCS, S3, or a zero-dependency local "dry run" bucket (a plain folder on disk)
used for development/demo when no real cloud credentials are configured.

    CLOUD_PROVIDER            gcs | s3 | dry_run          (default: dry_run)
    CLOUD_BUCKET_NAME         target bucket name          (default: see below)

    # GCS
    GCP_PROJECT_ID            GCP project that owns the bucket
    GOOGLE_APPLICATION_CREDENTIALS   path to a service-account JSON key
    GCS_LOCATION              bucket region, e.g. "US" (default: "US")

    # AWS S3
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY   or rely on ~/.aws/credentials
    AWS_REGION                e.g. "us-east-1"  (default: "us-east-1")
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
REJECTED_DIR = os.path.join(PROCESSED_DIR, "rejected")

# Local stand-in for a bucket, used by the "dry_run" provider. Lets the whole
# upload pipeline (bucket creation, key layout, retries, logging) be exercised
# and demoed with zero cloud credentials and zero network access.
DRY_RUN_BUCKET_ROOT = os.path.join(ROOT_DIR, "cloud_mock_bucket")

CLOUD_PROVIDER = os.environ.get("CLOUD_PROVIDER", "dry_run").lower()
CLOUD_BUCKET_NAME = os.environ.get(
    "CLOUD_BUCKET_NAME", "enterprise-ecommerce-supply-chain-data"
)

# --- GCS ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
GCS_LOCATION = os.environ.get("GCS_LOCATION", "US")

# --- AWS S3 ---
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

RETRY_MAX_ATTEMPTS = 5
RETRY_BASE_DELAY = 1.0

# --- Folder organization inside the bucket ---
# raw/<table>.csv                                        -- latest full source snapshot
# processed/<table>/<table>_<YYYYMMDDTHHMMSSZ>.csv        -- timestamped, so every
#                                                             upload is a new dated
#                                                             object (a simple, queryable
#                                                             data-lake versioning scheme)
# rejected/<table>/<original_filename>                     -- quarantined rows, for audit
RAW_PREFIX = "raw"
PROCESSED_PREFIX = "processed"
REJECTED_PREFIX = "rejected"
