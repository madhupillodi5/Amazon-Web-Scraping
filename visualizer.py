"""
visualizer.py
-------------
Generates the static PNG chart set (Matplotlib/Seaborn) used in reports, plus
Plotly figure builders reused by the interactive Streamlit dashboard.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe backend for script/CI usage
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

import config
from modules.utils import get_logger

logger = get_logger(__name__)
sns.set_theme(style="whitegrid")


class Visualizer:
    """Builds and saves the standard chart set for a cleaned, enriched DataFrame."""

    def __init__(self, df: pd.DataFrame, output_dir: Path = config.CHARTS_DIR):
        self.df = df
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save(self, fig, filename: str) -> Path:
        path = self.output_dir / filename
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved chart: %s", path)
        return path

    def price_distribution(self, filename: str = "price_distribution.png") -> Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.histplot(self.df["price"].dropna(), bins=20, kde=True, ax=ax, color="#2E86AB")
        ax.set_title("Price Distribution")
        ax.set_xlabel("Price ($)")
        ax.set_ylabel("Number of Products")
        return self._save(fig, filename)

    def price_vs_rating(self, filename: str = "price_vs_rating.png") -> Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        plot_df = self.df.copy()
        # Seaborn/Matplotlib can't handle pandas' nullable Int64 dtype directly.
        plot_df["review_count"] = plot_df["review_count"].astype("float64")
        sns.scatterplot(
            data=plot_df, x="price", y="rating", size="review_count",
            hue="sentiment_label" if "sentiment_label" in plot_df else None,
            sizes=(20, 300), alpha=0.7, ax=ax,
        )
        ax.set_title("Price vs. Rating (bubble size = review count)")
        ax.set_xlabel("Price ($)")
        ax.set_ylabel("Rating (stars)")
        return self._save(fig, filename)

    def brand_comparison(self, filename: str = "brand_comparison.png", top_n: int = 10) -> Path:
        top_brands = (
            self.df.groupby("brand")["price"].mean().sort_values(ascending=False).head(top_n)
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(x=top_brands.values, y=top_brands.index, ax=ax, color="#A23B72")
        ax.set_title(f"Average Price by Brand (Top {top_n})")
        ax.set_xlabel("Average Price ($)")
        ax.set_ylabel("Brand")
        return self._save(fig, filename)

    def sentiment_breakdown(self, filename: str = "sentiment_breakdown.png") -> Path:
        if "sentiment_label" not in self.df or self.df.empty:
            logger.warning("No sentiment data available; skipping sentiment chart")
            return None
        counts = self.df["sentiment_label"].value_counts()
        fig, ax = plt.subplots(figsize=(6, 6))
        colors = {"positive": "#3AAA35", "neutral": "#B0B0B0", "negative": "#D64545"}
        ax.pie(
            counts.values, labels=counts.index, autopct="%1.1f%%",
            colors=[colors.get(label, "#888") for label in counts.index], startangle=90,
        )
        ax.set_title("Review Sentiment Breakdown")
        return self._save(fig, filename)

    def value_score_leaderboard(self, filename: str = "value_leaderboard.png", top_n: int = 10) -> Path:
        top = self.df.sort_values("value_score", ascending=False).head(top_n)
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.barplot(x="value_score", y="title", data=top, color="#F18F01", ax=ax)
        ax.set_title(f"Top {top_n} Products by Value Score")
        ax.set_xlabel("Value Score (0-1)")
        ax.set_ylabel("")
        return self._save(fig, filename)

    def generate_all(self) -> list:
        """Generate the full standard chart set, skipping any that fail on empty data."""
        charts = []
        for method in (
            self.price_distribution, self.price_vs_rating, self.brand_comparison,
            self.sentiment_breakdown, self.value_score_leaderboard,
        ):
            try:
                result = method()
                if result:
                    charts.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Chart generation failed for %s: %s", method.__name__, exc)
        return charts


# --------------------------------------------------------------------------- #
# Plotly figure builders — reused by the interactive Streamlit dashboard
# --------------------------------------------------------------------------- #
def plotly_price_vs_rating(df: pd.DataFrame):
    return px.scatter(
        df, x="price", y="rating", size="review_count",
        color="sentiment_label" if "sentiment_label" in df else None,
        hover_name="title", title="Price vs. Rating",
    )


def plotly_price_trend(history_df: pd.DataFrame):
    return px.line(
        history_df, x="scraped_at", y="price", color="title",
        title="Price Trend Over Time", markers=True,
    )


def plotly_brand_comparison(df: pd.DataFrame, top_n: int = 10):
    top_brands = df.groupby("brand")["price"].mean().sort_values(ascending=False).head(top_n)
    return px.bar(
        top_brands, orientation="h",
        title=f"Average Price by Brand (Top {top_n})",
        labels={"value": "Average Price ($)", "brand": "Brand"},
    )
