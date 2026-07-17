import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import s3_utils


class _FakeClient:
    def __init__(self, exc):
        self._exc = exc

    def upload_file(self, *args, **kwargs):
        raise self._exc


def test_no_bucket_configured_skips_without_raising(monkeypatch):
    monkeypatch.setattr(s3_utils, "S3_BUCKET", "")
    key, status = s3_utils.upload_processed_file("/tmp/whatever.csv", "whatever.csv")
    assert key is None
    assert status == "skipped: S3_BUCKET not configured"


def test_s3_upload_failed_error_fails_soft_instead_of_raising(monkeypatch):
    # client.upload_file() (boto3's managed-transfer method) wraps a ClientError
    # like NoSuchBucket in its own S3UploadFailedError, which isn't a
    # BotoCoreError/ClientError subclass — regression test for that gap.
    from boto3.exceptions import S3UploadFailedError

    monkeypatch.setattr(s3_utils, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(
        "boto3.client",
        lambda *a, **kw: _FakeClient(S3UploadFailedError("NoSuchBucket: does not exist")),
    )

    key, status = s3_utils.upload_processed_file("/tmp/whatever.csv", "whatever.csv")

    assert key is None
    assert status.startswith("failed:")


def test_no_credentials_fails_soft(monkeypatch):
    from botocore.exceptions import NoCredentialsError

    monkeypatch.setattr(s3_utils, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr("boto3.client", lambda *a, **kw: _FakeClient(NoCredentialsError()))

    key, status = s3_utils.upload_processed_file("/tmp/whatever.csv", "whatever.csv")

    assert key is None
    assert status == "skipped: no AWS credentials"
