"""
Fake Shipping API (Source 3).

Simulates a third-party logistics provider's REST API: paginated, supports
an incremental "since" filter, and deliberately fails a configurable
percentage of requests with a 503 so the ETL client's retry logic has
something real to do.

Run standalone:
    python -m src.etl.shipping_api_server

Endpoints:
    GET /health
    GET /shipping?since=YYYY-MM-DD[ HH:MM:SS]&page=1&page_size=500
"""
import os
import random
import time

import pandas as pd
from flask import Flask, jsonify, request

from .config import RAW_DIR, SHIPPING_API_FAILURE_RATE, SHIPPING_API_HOST, SHIPPING_API_PORT
from src.utils.logging_setup import get_logger

logger = get_logger("etl.shipping_api_server")
app = Flask(__name__)

SHIPPING_CSV = os.path.join(RAW_DIR, "shipping.csv")
_cache = {"mtime": None, "df": None}


def _load_shipping_df() -> pd.DataFrame:
    """Re-reads shipping.csv only when it has changed on disk (cheap incremental cache)."""
    if not os.path.exists(SHIPPING_CSV):
        return pd.DataFrame(columns=[
            "shipping_id", "order_id", "route_id", "partner_id", "ship_date",
            "promised_delivery_date", "actual_delivery_date", "delivery_delay_days", "shipping_status",
        ])
    mtime = os.path.getmtime(SHIPPING_CSV)
    if _cache["mtime"] != mtime:
        logger.info("Reloading shipping.csv into the mock API's in-memory store (source file changed)")
        _cache["df"] = pd.read_csv(SHIPPING_CSV, parse_dates=["ship_date", "promised_delivery_date", "actual_delivery_date"])
        _cache["mtime"] = mtime
    return _cache["df"]


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/shipping", methods=["GET"])
def get_shipping():
    # Simulate a flaky upstream provider (timeouts / 5xx) so the client's
    # retry-with-backoff logic is genuinely exercised, not just decorative.
    if random.random() < SHIPPING_API_FAILURE_RATE:
        logger.warning("Injected transient failure (simulated 503)")
        time.sleep(0.2)
        return jsonify({"error": "Upstream logistics provider temporarily unavailable"}), 503

    since = request.args.get("since", "1970-01-01")
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 500)), 2000)

    df = _load_shipping_df()
    since_ts = pd.to_datetime(since, errors="coerce")
    filtered = df[df["ship_date"] >= since_ts] if pd.notna(since_ts) else df
    filtered = filtered.sort_values("ship_date")

    total_records = len(filtered)
    total_pages = max(1, -(-total_records // page_size))  # ceil div
    start, end = (page - 1) * page_size, page * page_size
    page_df = filtered.iloc[start:end].copy()

    for col in ["ship_date", "promised_delivery_date", "actual_delivery_date"]:
        if col in page_df.columns:
            page_df[col] = page_df[col].astype(str)

    return jsonify({
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "records": page_df.to_dict(orient="records"),
    })


if __name__ == "__main__":
    logger.info(f"Starting mock Shipping API on {SHIPPING_API_HOST}:{SHIPPING_API_PORT}")
    app.run(host=SHIPPING_API_HOST, port=SHIPPING_API_PORT, debug=False)
