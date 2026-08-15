"""
review_analyzer.py
-------------------
New feature: scores customer review text for sentiment so competitive
benchmarking isn't limited to star ratings alone. Uses TextBlob for a
lightweight, dependency-friendly polarity score in [-1, 1].
"""

from typing import List

import pandas as pd
from textblob import TextBlob

import config
from modules.utils import get_logger

logger = get_logger(__name__)


def score_review(text: str) -> float:
    """Return a polarity score in [-1 (negative), 1 (positive)] for a single review."""
    if not text or len(text) < config.MIN_REVIEW_LENGTH_FOR_SENTIMENT:
        return 0.0
    return round(TextBlob(text).sentiment.polarity, 3)


def label_sentiment(score: float) -> str:
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"


def analyze_reviews(reviews: List[str]) -> dict:
    """Aggregate sentiment across a product's review list."""
    if not reviews:
        return {"avg_sentiment": 0.0, "sentiment_label": "neutral", "review_scores": []}

    scores = [score_review(r) for r in reviews]
    avg = round(sum(scores) / len(scores), 3)
    return {
        "avg_sentiment": avg,
        "sentiment_label": label_sentiment(avg),
        "review_scores": scores,
    }


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add avg_sentiment / sentiment_label columns to a cleaned product DataFrame."""
    if df.empty:
        df["avg_sentiment"] = pd.Series(dtype=float)
        df["sentiment_label"] = pd.Series(dtype=str)
        return df

    logger.info("Scoring review sentiment for %d products", len(df))
    analyzed = df["reviews"].apply(analyze_reviews)
    df["avg_sentiment"] = analyzed.apply(lambda r: r["avg_sentiment"])
    df["sentiment_label"] = analyzed.apply(lambda r: r["sentiment_label"])
    return df
