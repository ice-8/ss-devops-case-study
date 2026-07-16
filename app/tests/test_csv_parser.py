import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from csv_parser import CsvParseError, parse_soh_csv, summarize

SAMPLE = (
    b'"211627629","Purple Safi Kaftan","4900.0000"\n'
    b'"211622324","White Logo-T-Shirt"," 450.0000"\n'
)


def test_parse_basic_rows():
    rows = parse_soh_csv(SAMPLE)
    assert len(rows) == 2
    assert rows[0]["sku"] == "211627629"
    assert rows[0]["description"] == "Purple Safi Kaftan"
    assert rows[0]["price"] == 4900.0


def test_parse_handles_leading_space_in_price():
    rows = parse_soh_csv(SAMPLE)
    assert rows[1]["price"] == 450.0


def test_summarize():
    rows = parse_soh_csv(SAMPLE)
    summary = summarize(rows)
    assert summary["row_count"] == 2
    assert summary["total_value"] == 5350.0


def test_rejects_empty_file():
    with pytest.raises(CsvParseError):
        parse_soh_csv(b"")


def test_rejects_bad_price():
    with pytest.raises(CsvParseError):
        parse_soh_csv(b'"123","Widget","not-a-number"\n')


def test_rejects_missing_columns():
    with pytest.raises(CsvParseError):
        parse_soh_csv(b'"123","Widget"\n')
