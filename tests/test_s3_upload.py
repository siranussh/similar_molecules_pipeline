import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import s3_upload  # noqa: E402


def test_upload_file_calls_client_and_returns_uri():
    fake_client = MagicMock()

    with patch.object(
        s3_upload, "get_s3_client", return_value=fake_client
    ):
        result = s3_upload.upload_file(
            "local_file.txt", "my-bucket", "some/key.txt"
        )

    fake_client.upload_file.assert_called_once_with(
        "local_file.txt", "my-bucket", "some/key.txt"
    )
    assert result == "s3://my-bucket/some/key.txt"


def test_get_s3_client_uses_default_region_when_unset(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)

    with patch.object(s3_upload.boto3, "client") as mock_boto_client:
        s3_upload.get_s3_client()

    called_kwargs = mock_boto_client.call_args[1]
    assert called_kwargs["region_name"] == "eu-central-1"


def test_get_s3_client_uses_env_region_when_set(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    with patch.object(s3_upload.boto3, "client") as mock_boto_client:
        s3_upload.get_s3_client()

    called_kwargs = mock_boto_client.call_args[1]
    assert called_kwargs["region_name"] == "us-east-1"
