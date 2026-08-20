from io import BytesIO
from unittest.mock import Mock

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from aws.s3_client import S3AccessDeniedError, S3ConfigurationError, S3ObjectNotFoundError, get_object_metadata, load_s3_config, read_csv_from_s3, verify_bucket_access


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "test"}}, "HeadObject")


def test_load_s3_config_requires_all_settings(monkeypatch):
    monkeypatch.setattr("aws.s3_client.load_dotenv", lambda *args, **kwargs: False)
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_BUCKET_NAME"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(S3ConfigurationError, match="AWS_ACCESS_KEY_ID"):
        load_s3_config()


def test_verify_bucket_access_calls_list_objects():
    client = Mock()
    verify_bucket_access(client, "example-bucket")
    client.list_objects_v2.assert_called_once_with(Bucket="example-bucket", Prefix="raw/sales.csv", MaxKeys=1)


def test_verify_bucket_access_maps_access_denied():
    client = Mock()
    client.list_objects_v2.side_effect = _client_error("AccessDenied")
    with pytest.raises(S3AccessDeniedError):
        verify_bucket_access(client, "example-bucket")


def test_get_object_metadata_maps_missing_object():
    client = Mock()
    client.head_object.side_effect = _client_error("NoSuchKey")
    with pytest.raises(S3ObjectNotFoundError):
        get_object_metadata(client, "example-bucket", "raw/sales.csv")


def test_read_csv_from_s3_returns_dataframe():
    client = Mock()
    client.get_object.return_value = {"Body": BytesIO(b"product,quantity\nWidget,2\n")}
    result = read_csv_from_s3(client, "example-bucket", "raw/sales.csv")
    pd.testing.assert_frame_equal(result, pd.DataFrame({"product": ["Widget"], "quantity": [2]}))
