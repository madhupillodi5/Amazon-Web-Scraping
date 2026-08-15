"""
parser.py
---------
Converts RawListing objects (which hold loosely-typed scraped text) into
structured, typed ProductRecord dictionaries ready for the cleaning stage.
Keeping parsing separate from scraping means the extraction logic can be
tested against saved HTML/fixtures without hitting the network.
"""

import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from modules.scraper import RawListing
from modules.utils import get_logger

logger = get_logger(__name__)

PRICE_RE = re.compile(r"[\d,]+\.?\d*")
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*out of")
DIGITS_RE = re.compile(r"[\d,]+")


@dataclass
class ProductRecord:
    title: str
    brand: Optional[str]
    price: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    specs: dict = field(default_factory=dict)
    reviews: List[str] = field(default_factory=list)
    url: str = ""


def _extract_price(price_text: str) -> Optional[float]:
    match = PRICE_RE.search(price_text.replace(",", ""))
    return float(match.group()) if match else None


def _extract_rating(rating_text: str) -> Optional[float]:
    match = RATING_RE.search(rating_text)
    return float(match.group(1)) if match else None


def _extract_review_count(review_text: str) -> Optional[int]:
    match = DIGITS_RE.search(review_text)
    return int(match.group().replace(",", "")) if match else None


def _guess_brand(title: str, specs: dict) -> Optional[str]:
    if specs.get("Brand"):
        return specs["Brand"]
    # Fall back to the first word of the title as a best-effort brand guess.
    return title.split()[0] if title else None


def parse_listing(raw: RawListing) -> ProductRecord:
    """Turn a single RawListing into a typed, cleaned-ish ProductRecord."""
    return ProductRecord(
        title=raw.title.strip(),
        brand=_guess_brand(raw.title, raw.specs),
        price=_extract_price(raw.price_text),
        rating=_extract_rating(raw.rating_text),
        review_count=_extract_review_count(raw.review_count_text),
        specs=raw.specs,
        reviews=raw.reviews,
        url=raw.url,
    )


def parse_listings(raw_listings: List[RawListing]) -> List[dict]:
    """Parse a batch of RawListings into a list of plain dicts (for easy DataFrame/JSON use)."""
    records = []
    for raw in raw_listings:
        try:
            records.append(asdict(parse_listing(raw)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping listing due to parse error: %s | title=%r", exc, raw.title)
    logger.info("Parsed %d/%d raw listings successfully", len(records), len(raw_listings))
    return records
