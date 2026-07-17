import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import records

SUMMARY = {"row_count": 2, "total_value": 5350.0}
ROWS = [
    {"line": 1, "sku": "211627629", "description": "Purple Safi Kaftan", "price": 4900.0},
    {"line": 2, "sku": "211622324", "description": "White Logo-T-Shirt", "price": 450.0},
]


def test_local_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "RECORDS_DIR", str(tmp_path))
    monkeypatch.setattr(records, "S3_BUCKET", "")

    record_id = records.save_processed_file("soh.csv", ROWS, SUMMARY, s3_key=None, s3_status="skipped")

    record = records.get_processed_file(record_id)
    assert record["filename"] == "soh.csv"
    assert record["row_count"] == 2
    assert record["rows"] == ROWS


def test_list_omits_rows_and_orders_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "RECORDS_DIR", str(tmp_path))
    monkeypatch.setattr(records, "S3_BUCKET", "")

    first_id = records.save_processed_file("a.csv", ROWS, SUMMARY, None, "skipped")
    second_id = records.save_processed_file("b.csv", ROWS, SUMMARY, None, "skipped")

    files = records.list_processed_files()
    assert [f["id"] for f in files] == [second_id, first_id]
    assert "rows" not in files[0]


def test_get_missing_record_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "RECORDS_DIR", str(tmp_path))
    monkeypatch.setattr(records, "S3_BUCKET", "")

    assert records.get_processed_file("nonexistent.json") is None


def test_rejects_path_traversal_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "RECORDS_DIR", str(tmp_path))
    monkeypatch.setattr(records, "S3_BUCKET", "")

    for bad_id in ["../../etc/passwd", "..", ".", ""]:
        assert records.get_processed_file(bad_id) is None
