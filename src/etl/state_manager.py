"""
Tracks a per-source "high-water mark" (the latest timestamp/date already
loaded) so re-running the pipeline only extracts new/changed rows instead of
reprocessing the entire dataset every time. State persists in a small JSON
file so it survives between runs.
"""
import json
import os
from datetime import datetime, timezone

from .config import STATE_FILE
from src.utils.logging_setup import get_logger

logger = get_logger("etl.state")


def _read_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def _write_state(state: dict) -> None:
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    os.replace(tmp_path, STATE_FILE)  # atomic swap, avoids a half-written state file


def get_watermark(source: str, default: str) -> str:
    state = _read_state()
    wm = state.get(source, {}).get("watermark", default)
    logger.debug(f"Watermark for '{source}': {wm}")
    return wm


def set_watermark(source: str, watermark: str, rows_loaded: int) -> None:
    state = _read_state()
    state[source] = {
        "watermark": str(watermark),
        "rows_loaded_last_run": int(rows_loaded),
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_state(state)
    logger.info(f"Updated watermark for '{source}' -> {watermark} ({rows_loaded} rows loaded)")


def get_full_state() -> dict:
    return _read_state()
