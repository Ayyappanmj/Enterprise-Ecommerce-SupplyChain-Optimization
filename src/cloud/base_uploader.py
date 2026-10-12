"""Common interface so upload_manager.py doesn't care whether it's talking to
GCS, S3, or the local dry-run stand-in."""
from abc import ABC, abstractmethod


class CloudUploader(ABC):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    @abstractmethod
    def ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't already exist. Must be idempotent -
        safe to call on every run."""

    @abstractmethod
    def upload_file(self, local_path: str, remote_key: str) -> str:
        """Upload one file to `remote_key` inside the bucket. Returns a
        provider-specific URI/path for logging."""

    @abstractmethod
    def object_exists(self, remote_key: str) -> bool:
        """Used to skip re-uploading a file that's already there."""
