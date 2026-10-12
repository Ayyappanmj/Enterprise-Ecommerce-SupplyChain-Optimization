"""
Configuration and documented business assumptions for Phase 5.

Where a metric can't be computed purely from the data (e.g. net margin needs
an operating-expense assumption; CLV needs a projection horizon), the
assumption is a named constant here rather than a magic number buried in
code, so it's easy to find, question, and change.
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLEANED_DIR = os.path.join(ROOT_DIR, "data", "processed", "cleaned")
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "processed", "features")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")

os.makedirs(FEATURES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# --- Business assumptions (documented, not hidden) ---

# Net margin = gross profit - shipping cost - refunds - assumed overhead.
# We don't have warehousing/payment-processing/overhead line items in the
# dataset, so they're approximated as a flat % of product revenue. This is a
# simplification a real project would replace with an actual cost allocation.
ASSUMED_OPEX_RATE = 0.08  # 8% of product revenue

# A shipment more than this many days late counts as "delayed" for the
# is_delayed flag and delay-bucket features (on top of the continuous
# delivery_delay_days figure, which is kept as-is).
DELAY_THRESHOLD_DAYS = 3

# Projected CLV horizon used for the simple projected_clv_usd feature
# (historical CLV - actual revenue to date - is also provided and does not
# depend on this assumption).
PROJECTED_CLV_HORIZON_YEARS = 3
