"""
data_cleaner.py
----------------
Pandas-based cleaning stage: takes the list of parsed product dicts and
produces a validated, de-duplicated, analysis-ready DataFrame.
"""

from typing import List

import pandas as pd

from modules.utils import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [
    "title", "brand", "price", "rating", "review_count", "specs", "reviews", "url",
]


class DataCleaner:
    """Encapsulates the cleaning pipeline so each step is testable in isolation."""

    def __init__(self, records: List[dict]):
        self.df = pd.DataFrame(records, columns=REQUIRED_COLUMNS)

    def drop_empty_titles(self) -> "DataCleaner":
        before = len(self.df)
        self.df = self.df[self.df["title"].astype(bool)]
        logger.info("Dropped %d rows with empty titles", before - len(self.df))
        return self

    def deduplicate(self) -> "DataCleaner":
        before = len(self.df)
        self.df = self.df.drop_duplicates(subset=["title", "url"], keep="first")
        logger.info("Dropped %d duplicate rows", before - len(self.df))
        return self

    def coerce_types(self) -> "DataCleaner":
        self.df["price"] = pd.to_numeric(self.df["price"], errors="coerce")
        self.df["rating"] = pd.to_numeric(self.df["rating"], errors="coerce")
        self.df["review_count"] = pd.to_numeric(
            self.df["review_count"], errors="coerce"
        ).astype("Int64")
        return self

    def drop_missing_essentials(self) -> "DataCleaner":
        before = len(self.df)
        self.df = self.df.dropna(subset=["price", "rating"])
        logger.info(
            "Dropped %d rows missing price or rating", before - len(self.df)
        )
        return self

    def flag_outliers(self, price_upper_pct: float = 0.99) -> "DataCleaner":
        """Flag (not drop) extreme price outliers so they can be filtered downstream if desired."""
        if self.df.empty:
            self.df["is_price_outlier"] = pd.Series(dtype=bool)
            return self
        cap = self.df["price"].quantile(price_upper_pct)
        self.df["is_price_outlier"] = self.df["price"] > cap
        logger.info("Flagged %d price outliers above the %.0fth percentile",
                    int(self.df["is_price_outlier"].sum()), price_upper_pct * 100)
        return self

    def add_value_score(self) -> "DataCleaner":
        """Simple composite score: higher rating & review volume, lower price, scores better."""
        if self.df.empty:
            self.df["value_score"] = pd.Series(dtype=float)
            return self
        normalized_price = self.df["price"] / self.df["price"].max()
        normalized_reviews = (
            self.df["review_count"].fillna(0) / max(self.df["review_count"].max(), 1)
        )
        self.df["value_score"] = (
            (self.df["rating"] / 5) * 0.5
            + normalized_reviews * 0.3
            + (1 - normalized_price) * 0.2
        ).round(3)
        return self

    def run(self) -> pd.DataFrame:
        """Execute the full cleaning pipeline in order and return the resulting DataFrame."""
        (
            self.drop_empty_titles()
            .deduplicate()
            .coerce_types()
            .drop_missing_essentials()
            .flag_outliers()
            .add_value_score()
        )
        self.df = self.df.reset_index(drop=True)
        logger.info("Cleaning complete: %d rows remain", len(self.df))
        return self.df
