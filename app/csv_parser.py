"""Parses stock-on-hand style CSVs: unheadered rows of (sku, description, price)."""
import csv
import io


class CsvParseError(ValueError):
    pass


def parse_soh_csv(raw_bytes: bytes) -> list[dict]:
    """Parse a soh.csv-style file into a list of {sku, description, price} rows.

    Format has no header row and looks like:
        "211627629","Purple Safi Kaftan","4900.0000"
    Price fields sometimes carry a leading space inside the quotes.
    """
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))

    rows = []
    for line_no, fields in enumerate(reader, start=1):
        if not fields or all(not f.strip() for f in fields):
            continue  # skip blank lines
        if len(fields) < 3:
            raise CsvParseError(f"line {line_no}: expected 3 columns, got {len(fields)}")

        sku, description, price_raw = fields[0].strip(), fields[1].strip(), fields[2].strip()
        try:
            price = float(price_raw)
        except ValueError:
            raise CsvParseError(f"line {line_no}: invalid price {price_raw!r}") from None

        rows.append({"line": line_no, "sku": sku, "description": description, "price": price})

    if not rows:
        raise CsvParseError("no data rows found in file")

    return rows


def summarize(rows: list[dict]) -> dict:
    total_value = sum(r["price"] for r in rows)
    return {
        "row_count": len(rows),
        "total_value": round(total_value, 2),
        "avg_price": round(total_value / len(rows), 2) if rows else 0,
    }
