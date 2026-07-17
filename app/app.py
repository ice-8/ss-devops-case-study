import logging
import os
import uuid

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from csv_parser import CsvParseError, parse_soh_csv, summarize
import records
from s3_utils import upload_processed_file

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")
MAX_CONTENT_LENGTH_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.post("/upload")
def upload():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("Please choose a CSV file to upload.", "error")
        return redirect(url_for("index"))

    if not file.filename.lower().endswith(".csv"):
        flash("Only .csv files are accepted.", "error")
        return redirect(url_for("index"))

    raw = file.read()
    try:
        rows = parse_soh_csv(raw)
    except CsvParseError as exc:
        flash(f"Could not parse {file.filename}: {exc}", "error")
        return redirect(url_for("index"))

    summary = summarize(rows)

    safe_name = f"{uuid.uuid4().hex[:8]}_{os.path.basename(file.filename)}"
    local_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(local_path, "wb") as f:
        f.write(raw)

    s3_key, s3_status = upload_processed_file(local_path, safe_name)

    record_id = records.save_processed_file(
        filename=file.filename,
        rows=rows,
        summary=summary,
        s3_key=s3_key,
        s3_status=s3_status,
    )

    return redirect(url_for("history_detail", file_id=record_id))


@app.get("/history")
def history():
    files = records.list_processed_files()
    return render_template("history.html", files=files)


@app.get("/history/<file_id>")
def history_detail(file_id):
    record = records.get_processed_file(file_id)
    if record is None:
        abort(404)
    return render_template("result.html", record=record)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
