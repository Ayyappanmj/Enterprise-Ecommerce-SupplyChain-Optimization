"""
Dry-run "uploader" that simulates a cloud bucket using a local folder
(cloud_mock_bucket/<bucket_name>/...). This lets the entire upload pipeline -
bucket creation, key/folder layout, retry behavior, logging, skip-if-exists -
be built, run, and demonstrated with zero cloud credentials and zero network
access. Swapping to real GCS or S3 is a one-line config change
(CLOUD_PROVIDER=gcs or s3); the calling code in upload_manager.py doesn't
change at all.
"""
import os
import shutil

from .base_uploader import CloudUploader
from .config import DRY_RUN_BUCKET_ROOT
from src.utils.logging_setup import get_logger

logger = get_logger("cloud.dry_run")


class DryRunUploader(CloudUploader):
    def __init__(self, bucket_name: str):
        super().__init__(bucket_name)
        self.bucket_path = os.path.join(DRY_RUN_BUCKET_ROOT, bucket_name)

    def ensure_bucket_exists(self) -> None:
        if not os.path.isdir(self.bucket_path):
            os.makedirs(self.bucket_path, exist_ok=True)
            logger.info(f"[dry_run] Created local mock bucket at {self.bucket_path}")
        else:
            logger.debug(f"[dry_run] Mock bucket already exists at {self.bucket_path}")

    def object_exists(self, remote_key: str) -> bool:
        return os.path.exists(os.path.join(self.bucket_path, remote_key))

    def upload_file(self, local_path: str, remote_key: str) -> str:
        dest = os.path.join(self.bucket_path, remote_key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)
        uri = f"dryrun://{self.bucket_name}/{remote_key}"
        logger.info(f"[dry_run] Uploaded {local_path} -> {uri}")
        return uri
