"""
S3-compatible storage backend.

Supports AWS S3, MinIO, and other S3-compatible storage services.
"""

from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING

import structlog

from pptx_hub.core.storage.base import StorageBackend

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = structlog.get_logger(__name__)


class S3Storage(StorageBackend):
    """
    S3-compatible storage backend.
    
    Works with AWS S3, MinIO, DigitalOcean Spaces, etc.
    
    Example:
        # AWS S3
        storage = S3Storage(
            bucket="my-bucket",
            access_key="...",
            secret_key="...",
        )
        
        # MinIO (self-hosted)
        storage = S3Storage(
            bucket="my-bucket",
            access_key="...",
            secret_key="...",
            endpoint_url="http://minio:9000",
        )
    """
    
    def __init__(
        self,
        bucket: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        """
        Initialize S3 storage.
        
        Args:
            bucket: S3 bucket name
            access_key: AWS access key (or use environment/IAM)
            secret_key: AWS secret key (or use environment/IAM)
            endpoint_url: Custom endpoint for S3-compatible services
            region: AWS region
        """
        try:
            import boto3
            from botocore.config import Config
        except ImportError as e:
            raise ImportError(
                "boto3 is required for S3 storage. "
                "Install with: pip install pptx-hub[storage]"
            ) from e
        
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        
        config = Config(signature_version="s3v4")
        
        client_kwargs = {
            "service_name": "s3",
            "region_name": region,
            "config": config,
        }
        
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        
        self.client: S3Client = boto3.client(**client_kwargs)
        self.log = logger.bind(storage="s3", bucket=bucket)
    
    def save(self, path: str, content: bytes) -> str:
        """Save content to S3."""
        content_type, _ = mimetypes.guess_type(path)
        
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        
        self.client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=content,
            **extra_args,
        )
        
        self.log.debug("file_saved", path=path, size=len(content))
        return f"s3://{self.bucket}/{path}"
    
    def read(self, path: str) -> bytes | None:
        """Read content from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=path)
            return response["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None
    
    def delete(self, path: str) -> bool:
        """Delete file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            self.log.debug("file_deleted", path=path)
            return True
        except Exception:
            return False
    
    def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Get pre-signed URL for S3 object.
        
        Args:
            path: Object key
            expires_in: URL expiration in seconds
            
        Returns:
            Pre-signed URL
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=expires_in,
        )
    
    def list_files(self, prefix: str = "") -> list[str]:
        """List files with given prefix."""
        files = []
        paginator = self.client.get_paginator("list_objects_v2")
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                files.append(obj["Key"])
        
        return files
    
    def get_size(self, path: str) -> int | None:
        """Get file size in bytes."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=path)
            return response["ContentLength"]
        except Exception:
            return None
