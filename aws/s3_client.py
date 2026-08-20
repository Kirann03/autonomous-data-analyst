"""Reusable, credential-safe S3 ingestion helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SALES_KEY = "raw/sales.csv"


class S3ConfigurationError(ValueError):
    """Raised when required S3 environment settings are missing."""


class S3ConnectionError(RuntimeError):
    """Raised when AWS cannot be reached or authenticated."""


class S3AccessDeniedError(S3ConnectionError):
    """Raised when IAM permissions deny a bucket or object request."""


class S3BucketNotFoundError(S3ConnectionError):
    """Raised when the configured bucket does not exist or is unavailable."""


class S3ObjectNotFoundError(S3ConnectionError):
    """Raised when the requested S3 object does not exist."""


@dataclass(frozen=True)
class S3Config:
    """Non-secret S3 connection settings."""

    region: str
    bucket_name: str


def load_s3_config() -> S3Config:
    """Load AWS settings from the project-root .env file without exposing secrets."""
    load_dotenv(PROJECT_ROOT / ".env")
    required = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_BUCKET_NAME")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise S3ConfigurationError(f"Missing required AWS environment variable(s): {', '.join(missing)}")
    return S3Config(region=os.environ["AWS_REGION"], bucket_name=os.environ["S3_BUCKET_NAME"])


def create_s3_client(config: S3Config | None = None) -> Any:
    """Create an S3 client; boto3 obtains credentials from environment variables."""
    config = config or load_s3_config()
    return boto3.client("s3", region_name=config.region)


def _raise_s3_error(error: Exception, *, object_key: str | None = None) -> None:
    """Convert boto errors to clear messages without including credential values."""
    if isinstance(error, EndpointConnectionError):
        raise S3ConnectionError("Unable to reach the configured AWS S3 endpoint.") from error
    if isinstance(error, BotoCoreError):
        raise S3ConnectionError("AWS client error. Check network connectivity and local AWS configuration.") from error
    if isinstance(error, ClientError):
        code = error.response.get("Error", {}).get("Code", "Unknown")
        if code in {"AccessDenied", "403"}:
            raise S3AccessDeniedError("AWS denied access to the configured S3 resource.") from error
        if code == "NoSuchBucket":
            raise S3BucketNotFoundError("The configured S3 bucket does not exist.") from error
        if code in {"NoSuchKey", "404", "NotFound"}:
            label = object_key or "requested"
            raise S3ObjectNotFoundError(f"The {label} S3 object does not exist.") from error
        if code in {"InvalidAccessKeyId", "SignatureDoesNotMatch", "ExpiredToken", "InvalidToken"}:
            raise S3ConnectionError("AWS credentials were rejected or have expired.") from error
        raise S3ConnectionError(f"S3 request failed with AWS error code: {code}.") from error
    raise error


def verify_bucket_access(client: Any, bucket_name: str) -> None:
    """Verify that the configured bucket can be reached with the current IAM identity."""
    try:
        # ListObjectsV2 maps directly to the bucket-restricted s3:ListBucket permission.
        client.list_objects_v2(Bucket=bucket_name, Prefix=DEFAULT_SALES_KEY, MaxKeys=1)
    except (BotoCoreError, ClientError) as error:
        _raise_s3_error(error)


def get_object_metadata(client: Any, bucket_name: str, object_key: str = DEFAULT_SALES_KEY) -> dict[str, Any]:
    """Verify an object exists and return its S3 metadata."""
    try:
        return client.head_object(Bucket=bucket_name, Key=object_key)
    except (BotoCoreError, ClientError) as error:
        _raise_s3_error(error, object_key=object_key)
    raise AssertionError("Unreachable")


def read_csv_from_s3(client: Any, bucket_name: str, object_key: str = DEFAULT_SALES_KEY) -> pd.DataFrame:
    """Download a CSV object from S3 and return it as a pandas DataFrame."""
    try:
        response = client.get_object(Bucket=bucket_name, Key=object_key)
        return pd.read_csv(response["Body"])
    except pd.errors.ParserError as error:
        raise ValueError(f"S3 object is not a valid CSV: {object_key}") from error
    except (BotoCoreError, ClientError) as error:
        _raise_s3_error(error, object_key=object_key)
    raise AssertionError("Unreachable")
