"""
Google Cloud Storage uploader.

Requires `pip install google-cloud-storage` and a service-account key:

    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    export GCP_PROJECT_ID=your-project-id
    export CLOUD_PROVIDER=gcs
    export CLOUD_BUCKET_NAME=your-bucket-name

The import of `google.cloud.storage` is deliberately deferred to __init__ (not
module level) so the rest of this codebase - and the dry_run/S3 uploaders -
work fine in environments where this package isn't installed.
"""
from .base_uploader import CloudUploader
from .config import GCP_PROJECT_ID, GCS_LOCATION, RETRY_BASE_DELAY, RETRY_MAX_ATTEMPTS
from src.utils.logging_setup import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger("cloud.gcs")


class GCSUploader(CloudUploader):
    def __init__(self, bucket_name: str):
        super().__init__(bucket_name)
        try:
            from google.cloud import storage
            from google.api_core.exceptions import GoogleAPIError
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage is not installed. Run: "
                "pip install google-cloud-storage --break-system-packages"
            ) from exc

        self._GoogleAPIError = GoogleAPIError
        self.client = storage.Client(project=GCP_PROJECT_ID)
        self._bucket = None

    def ensure_bucket_exists(self) -> None:
        from google.cloud.exceptions import NotFound

        try:
            self._bucket = self.client.get_bucket(self.bucket_name)
            logger.info(f"[gcs] Bucket already exists: gs://{self.bucket_name}")
        except NotFound:
            logger.info(f"[gcs] Bucket not found, creating: gs://{self.bucket_name}")
            self._bucket = self.client.create_bucket(self.bucket_name, location=GCS_LOCATION)
            logger.info(f"[gcs] Created bucket gs://{self.bucket_name} in {GCS_LOCATION}")

    def object_exists(self, remote_key: str) -> bool:
        return self._bucket.blob(remote_key).exists()

    def upload_file(self, local_path: str, remote_key: str) -> str:
        return self._upload_with_retry(local_path, remote_key)

    @retry_with_backoff(max_attempts=RETRY_MAX_ATTEMPTS, base_delay=RETRY_BASE_DELAY)
    def _upload_with_retry(self, local_path: str, remote_key: str) -> str:
        try:
            blob = self._bucket.blob(remote_key)
            blob.upload_from_filename(local_path)
        except self._GoogleAPIError as exc:
            logger.warning(f"[gcs] Transient upload error for {remote_key}: {exc}")
            raise
        uri = f"gs://{self.bucket_name}/{remote_key}"
        logger.info(f"[gcs] Uploaded {local_path} -> {uri}")
        return uri
