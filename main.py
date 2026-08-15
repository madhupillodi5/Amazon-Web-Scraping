"""
main.py
-------
Orchestrator for the full Amazon Product Intelligence pipeline. Wires
together every module in modules/:

    scraper -> parser -> data_cleaner -> review_analyzer -> database -> visualizer

Run `python main.py --help` for CLI options, or see README.md for examples.
"""

import argparse
import sys

import config
from modules.database import save_snapshot
from modules.data_cleaner import DataCleaner
from modules.parser import parse_listings
from modules.review_analyzer import enrich_dataframe
from modules.scraper import AmazonScraper
from modules.utils import get_logger
from modules.visualizer import Visualizer

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon product scraping & competitive benchmarking pipeline."
    )
    parser.add_argument("--query", required=True, help="Search term to benchmark")
    parser.add_argument("--pages", type=int, default=config.DEFAULT_PAGES,
                         help="Number of result pages to fetch (ignored in --demo mode)")
    parser.add_argument("--engine", choices=["requests", "selenium"], default="requests",
                         help="Scraping engine to use for live runs")
    parser.add_argument("--demo", action="store_true",
                         help="Run entirely on synthetic data — no network calls")
    parser.add_argument("--no-viz", action="store_true", help="Skip chart generation")
    return parser.parse_args()


def run_pipeline(query: str, pages: int, engine: str, demo: bool, generate_viz: bool) -> None:
    logger.info("=" * 70)
    logger.info("Starting pipeline | query=%r pages=%d engine=%s demo=%s", query, pages, engine, demo)

    # 1. Scrape (or generate synthetic data)
    scraper = AmazonScraper(engine=engine)
    raw_listings = (
        scraper.generate_demo_listings(query) if demo else scraper.search(query, pages)
    )
    if not raw_listings:
        logger.error("No listings retrieved for query=%r — aborting pipeline", query)
        sys.exit(1)
    logger.info("Retrieved %d raw listings", len(raw_listings))

    # 2. Parse raw HTML/text into structured records
    parsed_records = parse_listings(raw_listings)

    # 3. Clean & normalize with Pandas
    df = DataCleaner(parsed_records).run()
    if df.empty:
        logger.error("No valid rows survived cleaning — aborting pipeline")
        sys.exit(1)

    # 4. Enrich with review sentiment
    df = enrich_dataframe(df)

    # 5. Persist snapshot to SQLite for historical tracking
    save_snapshot(df, query)

    # 6. Export cleaned CSV
    safe_query = "".join(c if c.isalnum() else "_" for c in query.lower())
    csv_path = config.PROCESSED_DIR / f"{safe_query}_clean.csv"
    df.drop(columns=["specs", "reviews"], errors="ignore").to_csv(csv_path, index=False)
    logger.info("Exported cleaned data to %s", csv_path)

    # 7. Generate charts
    if generate_viz:
        chart_paths = Visualizer(df).generate_all()
        logger.info("Generated %d charts in %s", len(chart_paths), config.CHARTS_DIR)

    logger.info("Pipeline complete for query=%r. %d products analyzed.", query, len(df))
    logger.info("=" * 70)

    _print_summary(df, query)


def _print_summary(df, query: str) -> None:
    print(f"\nSummary for '{query}'")
    print("-" * 50)
    print(f"Products analyzed : {len(df)}")
    print(f"Average price     : ${df['price'].mean():.2f}")
    print(f"Average rating    : {df['rating'].mean():.2f} / 5")
    if "sentiment_label" in df:
        print(f"Sentiment split   : {df['sentiment_label'].value_counts().to_dict()}")
    if "value_score" in df and not df.empty:
        top = df.sort_values("value_score", ascending=False).iloc[0]
        print(f"Best value pick   : {top['title']} (${top['price']:.2f}, {top['rating']}★)")
    print(f"\nCleaned CSV       : {config.PROCESSED_DIR}")
    print(f"Charts            : {config.CHARTS_DIR}")
    print(f"Database          : {config.DB_PATH}\n")


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        query=args.query,
        pages=args.pages,
        engine=args.engine,
        demo=args.demo,
        generate_viz=not args.no_viz,
    )
