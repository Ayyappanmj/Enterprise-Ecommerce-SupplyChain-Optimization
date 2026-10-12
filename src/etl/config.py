import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
REJECTED_DIR = os.path.join(PROCESSED_DIR, "rejected")
STATE_DIR = os.path.join(PROCESSED_DIR, "_state")
STATE_FILE = os.path.join(STATE_DIR, "etl_state.json")

for d in (PROCESSED_DIR, REJECTED_DIR, STATE_DIR):
    os.makedirs(d, exist_ok=True)

# Mock Shipping API (Source 3)
SHIPPING_API_HOST = os.environ.get("SHIPPING_API_HOST", "127.0.0.1")
SHIPPING_API_PORT = int(os.environ.get("SHIPPING_API_PORT", "5055"))
SHIPPING_API_BASE_URL = f"http://{SHIPPING_API_HOST}:{SHIPPING_API_PORT}"
SHIPPING_API_PAGE_SIZE = 500
SHIPPING_API_FAILURE_RATE = float(os.environ.get("SHIPPING_API_FAILURE_RATE", "0.08"))
SHIPPING_API_REQUEST_TIMEOUT = 5  # seconds

RETRY_MAX_ATTEMPTS = 5
RETRY_BASE_DELAY = 0.5

DEFAULT_WATERMARK = "1970-01-01"  # used the first time a source is ever loaded
