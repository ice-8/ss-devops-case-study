"""Tiny SQLite-backed history store for processed CSV files.

Rows are stored alongside the metadata so "previously processed files" can be
displayed instantly even after the source object transitions to S3 Glacier
(where a live GET would be slow/costly).
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "/data/history.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    total_value REAL NOT NULL,
    s3_key TEXT,
    s3_status TEXT NOT NULL,
    rows_json TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)


def save_processed_file(filename, rows, summary, s3_key, s3_status):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO processed_files
               (filename, uploaded_at, row_count, total_value, s3_key, s3_status, rows_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                filename,
                datetime.now(timezone.utc).isoformat(),
                summary["row_count"],
                summary["total_value"],
                s3_key,
                s3_status,
                json.dumps(rows),
            ),
        )
        return cur.lastrowid


def list_processed_files(limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id, filename, uploaded_at, row_count, total_value, s3_key, s3_status "
            "FROM processed_files ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_processed_file(file_id):
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM processed_files WHERE id = ?", (file_id,))
        row = cur.fetchone()
        if row is None:
            return None
        record = dict(row)
        record["rows"] = json.loads(record.pop("rows_json"))
        return record
