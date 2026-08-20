"""Run a real, credential-safe connectivity test for the configured S3 sales object."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aws.s3_client import (
    DEFAULT_SALES_KEY,
    S3ConnectionError,
    S3ConfigurationError,
    create_s3_client,
    get_object_metadata,
    load_s3_config,
    read_csv_from_s3,
    verify_bucket_access,
)


LOCAL_SALES_FILE = PROJECT_ROOT / "data" / "raw" / "sales.csv"


def main() -> int:
    try:
        config = load_s3_config()
        client = create_s3_client(config)
        bucket_access = True
        try:
            verify_bucket_access(client, config.bucket_name)
            print("Bucket access: PASS")
        except S3ConnectionError as error:
            bucket_access = False
            print("Bucket access: FAIL")
            print(f"Bucket test error: {error}")

        metadata = get_object_metadata(client, config.bucket_name, DEFAULT_SALES_KEY)
        print("AWS connection: PASS")
        print("Object exists: PASS")
        print(f"AWS region: {config.region}")
        print(f"Bucket name: {config.bucket_name}")
        print(f"Object key: {DEFAULT_SALES_KEY}")
        print(f"Object size: {metadata.get('ContentLength', 0)} bytes")
        s3_data = read_csv_from_s3(client, config.bucket_name, DEFAULT_SALES_KEY)
        local_data = pd.read_csv(LOCAL_SALES_FILE)
        matches = len(s3_data) == len(local_data) and len(s3_data.columns) == len(local_data.columns) and s3_data.columns.tolist() == local_data.columns.tolist()
        print(f"CSV rows: {len(s3_data)}")
        print(f"CSV columns: {len(s3_data.columns)}")
        print(f"Column names: {', '.join(s3_data.columns)}")
        print(f"Local CSV rows: {len(local_data)}")
        print(f"Local comparison: {'MATCH' if matches else 'MISMATCH'}")
        return 0 if bucket_access and matches else 1
    except (S3ConfigurationError, S3ConnectionError) as error:
        print("AWS connection: FAIL")
        print("Bucket access: FAIL")
        print("Object exists: FAIL")
        print(f"S3 test error: {error}")
    except Exception as error:
        print("AWS connection: FAIL")
        print(f"S3 test error: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
