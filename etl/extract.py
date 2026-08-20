"""Data extraction helpers."""

from pathlib import Path

import pandas as pd

from aws.s3_client import DEFAULT_SALES_KEY, create_s3_client, load_s3_config, read_csv_from_s3


def extract_csv(file_path: str | Path, **read_csv_options: object) -> pd.DataFrame:
    """Read a CSV file after validating its existence and extension."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Expected a file, received: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Only CSV files are supported, received: {path.suffix or 'no extension'}")
    try:
        return pd.read_csv(path, **read_csv_options)
    except pd.errors.ParserError as error:
        raise ValueError(f"CSV file could not be parsed: {path}") from error


def extract_s3_csv(object_key: str = DEFAULT_SALES_KEY, *, client: object | None = None) -> pd.DataFrame:
    """Read a configured S3 CSV into a DataFrame without requiring a local file."""
    config = load_s3_config()
    s3_client = client or create_s3_client(config)
    return read_csv_from_s3(s3_client, config.bucket_name, object_key)
