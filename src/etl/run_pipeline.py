"""
Multi-source ETL pipeline orchestrator (Phase 2).

    Source 1: Web Orders CSV        -> extract_web_orders.py
    Source 2: Inventory System CSV  -> extract_inventory.py
    Source 3: Shipping API (Flask)  -> extract_shipping_api.py  (needs shipping_api_server.py running)

For each source: extract (incremental, since last watermark) -> validate
(quarantine bad rows) -> transform (standardize + tag) -> load (append to
data/processed/) -> advance the watermark, but only on success.

A failure in one source is logged and does NOT stop the other two sources
from running - each source is isolated in its own try/except so a broken
Shipping API, say, doesn't block Web Orders or Inventory from loading.

Usage:
    python -m src.etl.run_pipeline
    python -m src.etl.run_pipeline --sources web_orders inventory
"""
import argparse
import sys
import time

import pandas as pd

from . import extract_web_orders, extract_inventory, extract_shipping_api
from . import validators, transform, load as load_module, state_manager
from .config import DEFAULT_WATERMARK
from .exceptions import ETLError
from src.utils.logging_setup import get_logger

logger = get_logger("etl.pipeline")

SOURCES = {
    "web_orders": {
        "extract": extract_web_orders.extract,
        "validate": validators.validate_web_orders,
        "watermark_col": "order_date",
        "table_name": "orders",
    },
    "inventory": {
        "extract": extract_inventory.extract,
        "validate": validators.validate_inventory,
        "watermark_col": "last_restock_date",
        "table_name": "inventory",
    },
    "shipping_api": {
        "extract": extract_shipping_api.extract,
        "validate": validators.validate_shipping,
        "watermark_col": "ship_date",
        "table_name": "shipping",
    },
}


def run_source(source_name: str) -> dict:
    cfg = SOURCES[source_name]
    result = {"source": source_name, "status": "ok", "extracted": 0, "loaded": 0, "rejected": 0, "error": None}
    t0 = time.time()

    try:
        watermark = state_manager.get_watermark(source_name, DEFAULT_WATERMARK)
        logger.info(f"--- [{source_name}] starting (watermark={watermark}) ---")

        raw_df = cfg["extract"](watermark)
        result["extracted"] = len(raw_df)
        if raw_df.empty:
            logger.info(f"[{source_name}] no new data since {watermark}")
            result["status"] = "no_new_data"
            return result

        valid_df, rejected_df, issues = cfg["validate"](raw_df)
        result["rejected"] = len(rejected_df)
        load_module.quarantine(rejected_df, cfg["table_name"])

        valid_df = transform.standardize_dates(valid_df, [cfg["watermark_col"]])
        valid_df = transform.add_ingestion_metadata(valid_df, source_name)

        loaded = load_module.load(valid_df, cfg["table_name"])
        result["loaded"] = loaded

        if not valid_df.empty:
            new_watermark = valid_df[cfg["watermark_col"]].max()
            state_manager.set_watermark(source_name, new_watermark, loaded)

        logger.info(f"--- [{source_name}] done in {time.time() - t0:.2f}s: "
                     f"{result['extracted']} extracted, {loaded} loaded, {result['rejected']} rejected ---")

    except ETLError as exc:
        logger.error(f"[{source_name}] FAILED (pipeline error): {exc}")
        result["status"], result["error"] = "failed", str(exc)
    except Exception as exc:  # noqa: BLE001 - top-level safety net so one source can't crash the run
        logger.exception(f"[{source_name}] FAILED (unexpected error): {exc}")
        result["status"], result["error"] = "failed", str(exc)

    return result


def main(source_names=None):
    source_names = source_names or list(SOURCES.keys())
    logger.info(f"=== ETL run starting for sources: {source_names} ===")

    results = [run_source(name) for name in source_names]

    print("\n" + "=" * 70)
    print(f"{'SOURCE':<16}{'STATUS':<14}{'EXTRACTED':>10}{'LOADED':>10}{'REJECTED':>10}")
    print("-" * 70)
    for r in results:
        print(f"{r['source']:<16}{r['status']:<14}{r['extracted']:>10}{r['loaded']:>10}{r['rejected']:>10}")
    print("=" * 70)

    failed = [r for r in results if r["status"] == "failed"]
    if failed:
        logger.warning(f"{len(failed)} source(s) failed this run: {[r['source'] for r in failed]}")
        sys.exit(1)
    logger.info("=== ETL run complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the multi-source ETL pipeline")
    parser.add_argument("--sources", nargs="+", choices=list(SOURCES.keys()), default=None,
                         help="Subset of sources to run (default: all)")
    args = parser.parse_args()
    main(args.sources)
