"""Processed-file history: S3-backed when a bucket is configured, local JSON
files otherwise. Same interface either way, so app.py doesn't care which one
is active — chosen once, at import time, from S3_BUCKET.

Each processed upload is one small JSON record (metadata + parsed rows),
keyed by a timestamp-prefixed id so listing is just a lexicographic sort.
On S3 these live under records/ — a separate prefix from processed/ (the
raw CSVs) so records are never subject to the Glacier lifecycle rule and
stay instantly readable regardless of how old the source file is.
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
RECORDS_PREFIX = "records/"
RECORDS_DIR = os.environ.get("RECORDS_DIR", "/data/records")

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _s3():
    import boto3

    return boto3.client("s3", region_name=AWS_REGION)


def _new_id(filename: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    safe_name = _SAFE_CHARS.sub("_", os.path.basename(filename))
    return f"{ts}_{uuid.uuid4().hex[:8]}_{safe_name}.json"


def _valid_id(record_id: str) -> bool:
    return bool(record_id) and "/" not in record_id and record_id not in (".", "..")


def _write(record_id: str, body: bytes) -> None:
    if S3_BUCKET:
        _s3().put_object(
            Bucket=S3_BUCKET, Key=RECORDS_PREFIX + record_id, Body=body,
            ContentType="application/json",
        )
    else:
        os.makedirs(RECORDS_DIR, exist_ok=True)
        with open(os.path.join(RECORDS_DIR, record_id), "wb") as f:
            f.write(body)


def _read(record_id: str) -> dict | None:
    if not _valid_id(record_id):
        return None
    try:
        if S3_BUCKET:
            body = _s3().get_object(Bucket=S3_BUCKET, Key=RECORDS_PREFIX + record_id)["Body"].read()
        else:
            with open(os.path.join(RECORDS_DIR, record_id), "rb") as f:
                body = f.read()
    except Exception:
        logger.warning("Could not read record %s", record_id, exc_info=True)
        return None
    return json.loads(body)


def _list_ids() -> list[str]:
    if S3_BUCKET:
        resp = _s3().list_objects_v2(Bucket=S3_BUCKET, Prefix=RECORDS_PREFIX)
        ids = [obj["Key"][len(RECORDS_PREFIX):] for obj in resp.get("Contents", [])]
    else:
        os.makedirs(RECORDS_DIR, exist_ok=True)
        ids = os.listdir(RECORDS_DIR)
    return sorted(ids, reverse=True)  # timestamp-prefixed -> newest first


def save_processed_file(filename, rows, summary, s3_key, s3_status) -> str:
    record_id = _new_id(filename)
    body = json.dumps({
        "filename": filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": summary["row_count"],
        "total_value": summary["total_value"],
        "s3_key": s3_key,
        "s3_status": s3_status,
        "rows": rows,
    }).encode("utf-8")
    _write(record_id, body)
    return record_id


def list_processed_files(limit: int = 50) -> list[dict]:
    files = []
    for record_id in _list_ids()[:limit]:
        record = _read(record_id)
        if record is not None:
            files.append({"id": record_id, **{k: v for k, v in record.items() if k != "rows"}})
    return files


def get_processed_file(record_id: str) -> dict | None:
    record = _read(record_id)
    if record is None:
        return None
    return {"id": record_id, **record}
