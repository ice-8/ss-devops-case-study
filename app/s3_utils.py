"""S3 upload wrapper that fails soft when credentials/bucket aren't configured.

Kept deliberately simple: the case study asks the app to push processed files
to S3, with the bucket's lifecycle (Glacier transition) managed separately in
infra/s3 (Terraform). This module just needs to attempt the upload and report
a clear status back to the caller.
"""
import logging
import os

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PREFIX = os.environ.get("S3_PREFIX", "processed/")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")


def upload_processed_file(local_path: str, filename: str) -> tuple[str | None, str]:
    """Upload a file to S3. Returns (s3_key_or_None, status_message)."""
    if not S3_BUCKET:
        return None, "skipped: S3_BUCKET not configured"

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    except ImportError:
        return None, "skipped: boto3 not installed"

    key = f"{S3_PREFIX}{filename}"
    try:
        client = boto3.client("s3", region_name=AWS_REGION)
        client.upload_file(local_path, S3_BUCKET, key)
        return key, "uploaded"
    except NoCredentialsError:
        logger.warning("S3 upload skipped: no AWS credentials available")
        return None, "skipped: no AWS credentials"
    except (BotoCoreError, ClientError) as exc:
        logger.warning("S3 upload failed: %s", exc)
        return None, f"failed: {exc}"
