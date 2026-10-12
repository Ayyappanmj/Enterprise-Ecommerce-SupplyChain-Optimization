"""
Ties together: provider selection, bucket creation, and the upload plan that
gives the bucket its folder organization:

    raw/<table>.csv
    processed/<table>/<table>_<UPLOADED_AT_UTC>.csv
    rejected/<table>/<original_filename>

Re-running the upload is safe and cheap: raw/ objects are overwritten in
place (they're a "latest snapshot"), while processed/ and rejected/ objects
are timestamped so nothing is ever clobbered and skip-if-exists avoids
re-uploading a file byte-for-byte identical to one already there.
"""
import os
from datetime import datetime, timezone

from .config import (
    CLOUD_PROVIDER, CLOUD_BUCKET_NAME, RAW_DIR, PROCESSED_DIR, REJECTED_DIR,
    RAW_PREFIX, PROCESSED_PREFIX, REJECTED_PREFIX,
)
from src.utils.logging_setup import get_logger

logger = get_logger("cloud.upload_manager")


def get_uploader(provider: str = None, bucket_name: str = None):
    provider = (provider or CLOUD_PROVIDER).lower()
    bucket_name = bucket_name or CLOUD_BUCKET_NAME

    if provider == "gcs":
        from .gcs_uploader import GCSUploader
        return GCSUploader(bucket_name)
    if provider == "s3":
        from .s3_uploader import S3Uploader
        return S3Uploader(bucket_name)
    if provider == "dry_run":
        from .dry_run_uploader import DryRunUploader
        return DryRunUploader(bucket_name)
    raise ValueError(f"Unknown CLOUD_PROVIDER '{provider}'. Use gcs, s3, or dry_run.")


def _table_name(filename: str) -> str:
    return os.path.splitext(filename)[0]


def build_upload_plan(upload_raw=True, upload_processed=True, upload_rejected=True):
    """Returns a list of (local_path, remote_key) tuples implementing the
    bucket's folder organization."""
    plan = []
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if upload_raw and os.path.isdir(RAW_DIR):
        for fname in sorted(os.listdir(RAW_DIR)):
            if fname.startswith("."):
                continue
            local_path = os.path.join(RAW_DIR, fname)
            if os.path.isfile(local_path):
                plan.append((local_path, f"{RAW_PREFIX}/{fname}"))

    if upload_processed and os.path.isdir(PROCESSED_DIR):
        for fname in sorted(os.listdir(PROCESSED_DIR)):
            local_path = os.path.join(PROCESSED_DIR, fname)
            if os.path.isfile(local_path) and fname.endswith(".csv"):
                table = _table_name(fname)
                remote_key = f"{PROCESSED_PREFIX}/{table}/{table}_{run_ts}.csv"
                plan.append((local_path, remote_key))

    if upload_rejected and os.path.isdir(REJECTED_DIR):
        for fname in sorted(os.listdir(REJECTED_DIR)):
            local_path = os.path.join(REJECTED_DIR, fname)
            if os.path.isfile(local_path) and fname.endswith(".csv"):
                # rejected filenames already carry their own timestamp; group by table.
                table = fname.split("_rejected_")[0]
                plan.append((local_path, f"{REJECTED_PREFIX}/{table}/{fname}"))

    return plan


def run(provider: str = None, bucket_name: str = None,
        upload_raw=True, upload_processed=True, upload_rejected=True, skip_existing=True):
    uploader = get_uploader(provider, bucket_name)
    logger.info(f"=== Cloud upload starting: provider={provider or CLOUD_PROVIDER}, "
                f"bucket={bucket_name or CLOUD_BUCKET_NAME} ===")

    uploader.ensure_bucket_exists()
    plan = build_upload_plan(upload_raw, upload_processed, upload_rejected)

    uploaded, skipped, failed = [], [], []
    for local_path, remote_key in plan:
        try:
            if skip_existing and uploader.object_exists(remote_key):
                logger.debug(f"Skipping (already exists): {remote_key}")
                skipped.append(remote_key)
                continue
            uri = uploader.upload_file(local_path, remote_key)
            uploaded.append(uri)
        except Exception as exc:
            logger.error(f"Failed to upload {local_path} -> {remote_key}: {exc}")
            failed.append((local_path, str(exc)))

    logger.info(f"=== Cloud upload complete: {len(uploaded)} uploaded, "
                f"{len(skipped)} skipped, {len(failed)} failed ===")
    return {"uploaded": uploaded, "skipped": skipped, "failed": failed}
