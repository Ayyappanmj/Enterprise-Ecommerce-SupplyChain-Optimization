"""
CLI entrypoint for uploading data/raw, data/processed and data/processed/rejected
to cloud storage.

Usage:
    python -m src.cloud.run_upload                          # uses CLOUD_PROVIDER env (default: dry_run)
    python -m src.cloud.run_upload --provider dry_run
    python -m src.cloud.run_upload --provider gcs --bucket my-bucket
    python -m src.cloud.run_upload --provider s3  --bucket my-bucket --only processed
"""
import argparse
import sys

from . import upload_manager
from src.utils.logging_setup import get_logger

logger = get_logger("cloud.cli")


def main():
    parser = argparse.ArgumentParser(description="Upload local data to cloud storage")
    parser.add_argument("--provider", choices=["gcs", "s3", "dry_run"], default=None,
                         help="Cloud provider (default: $CLOUD_PROVIDER or dry_run)")
    parser.add_argument("--bucket", default=None, help="Bucket name (default: $CLOUD_BUCKET_NAME)")
    parser.add_argument("--only", choices=["raw", "processed", "rejected", "all"], default="all")
    parser.add_argument("--no-skip-existing", action="store_true",
                         help="Re-upload files even if an object with the same key already exists")
    args = parser.parse_args()

    result = upload_manager.run(
        provider=args.provider,
        bucket_name=args.bucket,
        upload_raw=args.only in ("raw", "all"),
        upload_processed=args.only in ("processed", "all"),
        upload_rejected=args.only in ("rejected", "all"),
        skip_existing=not args.no_skip_existing,
    )

    print("\n" + "=" * 60)
    print(f"Uploaded : {len(result['uploaded'])}")
    print(f"Skipped  : {len(result['skipped'])}")
    print(f"Failed   : {len(result['failed'])}")
    print("=" * 60)

    if result["failed"]:
        for local_path, err in result["failed"]:
            print(f"  FAILED: {local_path} -> {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
