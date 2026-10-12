import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
CLEANED_DIR = os.path.join(ROOT_DIR, "data", "processed", "cleaned")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Approximate standard-time UTC offset (hours) per country, used only to
# demonstrate timezone normalization on synthetic timestamps. Real production
# code would use a proper tz database (zoneinfo/pytz) keyed by an IANA name
# and would account for DST; this is a deliberately simple stand-in since the
# generated dataset has no real per-record timezone info to normalize.
COUNTRY_UTC_OFFSET_HOURS = {
    "United States": -5, "Canada": -5, "Mexico": -6,
    "United Kingdom": 0, "Germany": 1, "France": 1, "Italy": 1, "Spain": 1,
    "Netherlands": 1, "Poland": 1, "Sweden": 1,
    "China": 8, "Japan": 9, "India": 5.5, "South Korea": 9, "Australia": 10,
    "Singapore": 8, "Indonesia": 7, "Vietnam": 7, "Thailand": 7,
    "Brazil": -3, "Argentina": -3, "Chile": -4, "Colombia": -5, "Peru": -5,
    "United Arab Emirates": 4, "Saudi Arabia": 3, "South Africa": 2,
    "Egypt": 2, "Nigeria": 1,
}

IQR_MULTIPLIER = 1.5  # standard Tukey's-fence outlier threshold
