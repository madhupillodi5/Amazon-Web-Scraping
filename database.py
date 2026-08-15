"""
database.py
-----------
New feature: persists each pipeline run's snapshot to a local SQLite
database so price and rating history can be tracked across multiple runs,
not just analyzed as a single point-in-time snapshot.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import pandas as pd

import config
from modules.utils import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS product_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    title TEXT NOT NULL,
    brand TEXT,
    price REAL,
    rating REAL,
    review_count INTEGER,
    avg_sentiment REAL,
    sentiment_label TEXT,
    value_score REAL,
    url TEXT,
    scraped_at TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_snapshot(df: pd.DataFrame, query: str) -> int:
    """Insert the current cleaned/enriched DataFrame as a timestamped snapshot. Returns row count."""
    if df.empty:
        logger.warning("No rows to save for query='%s'", query)
        return 0

    timestamp = datetime.now(timezone.utc).isoformat()
    records = df.copy()
    records["query"] = query
    records["scraped_at"] = timestamp

    columns = [
        "query", "title", "brand", "price", "rating", "review_count",
        "avg_sentiment", "sentiment_label", "value_score", "url", "scraped_at",
    ]
    for col in columns:
        if col not in records.columns:
            records[col] = None

    with _connect() as conn:
        records[columns].to_sql("product_snapshots", conn, if_exists="append", index=False)

    logger.info("Saved %d rows to %s for query='%s'", len(records), config.DB_PATH, query)
    return len(records)


def load_price_history(query: str) -> pd.DataFrame:
    """Return all historical snapshots for a given query, ordered by time."""
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM product_snapshots WHERE query = ? ORDER BY scraped_at",
            conn, params=(query,),
        )


def load_all_queries() -> list:
    """List distinct queries that have been stored, for dashboard dropdowns etc."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT query FROM product_snapshots").fetchall()
    return [r[0] for r in rows]
