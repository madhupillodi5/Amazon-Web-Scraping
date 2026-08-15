"""
config.py
---------
Central configuration for the pipeline: filesystem paths, HTTP behavior,
and scraping etiquette settings. Keeping this in one place means no module
needs to hard-code a path, header, or delay value.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHARTS_DIR = PROCESSED_DIR / "charts"
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "amazon_products.sqlite"
LOG_DIR = BASE_DIR / "logs"

for directory in (RAW_DIR, PROCESSED_DIR, CHARTS_DIR, DB_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# HTTP / scraping etiquette
# ---------------------------------------------------------------------------
BASE_URL = "https://www.amazon.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

# Minimum/maximum seconds to wait between requests (randomized within range).
REQUEST_DELAY_RANGE = (2.5, 5.5)

# Retry behavior for transient failures (timeouts, 429s, 5xx).
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.8
REQUEST_TIMEOUT = 12  # seconds

# ---------------------------------------------------------------------------
# Pipeline defaults
# ---------------------------------------------------------------------------
DEFAULT_PAGES = 1
MIN_REVIEW_LENGTH_FOR_SENTIMENT = 8  # characters, skip near-empty reviews
