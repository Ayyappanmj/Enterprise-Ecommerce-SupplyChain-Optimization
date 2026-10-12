"""
AWS S3 uploader (alternative to GCS, per the project's "GCS or S3 free tier" spec).

Requires `pip install boto3` and credentials, either via environment variables
or the default ~/.aws/credentials chain:

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    export AWS_REGION=us-east-1
    export CLOUD_PROVIDER=s3
    export CLOUD_BUCKET_NAME=your-bucket-name

The import of boto3 is deferred to __init__ so the rest of the codebase works
fine without it installed.
"""
from .base_uploader import CloudUploader
from .config import AWS_REGION, RETRY_BASE_DELAY, RETRY_MAX_ATTEMPTS
from src.utils.logging_setup import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger("cloud.s3")


class S3Uploader(CloudUploader):
    def __init__(self, bucket_name: str):
        super().__init__(bucket_name)
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise ImportError(
                "boto3 is not installed. Run: pip install boto3 --break-system-packages"
            ) from exc

        self._ClientError = ClientError
        self.region = AWS_REGION
        self.client = boto3.client("s3", region_name=self.region)

    def ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"[s3] Bucket already exists: s3://{self.bucket_name}")
        except self._ClientError as exc:
            status = exc.response.get("Error", {}).get("Code")
            if status in ("404", "NoSuchBucket"):
                logger.info(f"[s3] Bucket not found, creating: s3://{self.bucket_name}")
                kwargs = {"Bucket": self.bucket_name}
                if self.region != "us-east-1":
                    kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.region}
                self.client.create_bucket(**kwargs)
                logger.info(f"[s3] Created bucket s3://{self.bucket_name} in {self.region}")
            else:
                raise

    def object_exists(self, remote_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except self._ClientError:
            return False

    def upload_file(self, local_path: str, remote_key: str) -> str:
        return self._upload_with_retry(local_path, remote_key)

    @retry_with_backoff(max_attempts=RETRY_MAX_ATTEMPTS, base_delay=RETRY_BASE_DELAY)
    def _upload_with_retry(self, local_path: str, remote_key: str) -> str:
        try:
            self.client.upload_file(local_path, self.bucket_name, remote_key)
        except self._ClientError as exc:
            logger.warning(f"[s3] Transient upload error for {remote_key}: {exc}")
            raise
        uri = f"s3://{self.bucket_name}/{remote_key}"
        logger.info(f"[s3] Uploaded {local_path} -> {uri}")
        return uri
