"""
scraper.py
----------
Fetches raw product listing pages. Two engines are supported:

    - "requests"  : fast, lightweight, uses requests + urllib3's retry-capable
                    Session. Good for static/server-rendered pages.
    - "selenium"  : falls back to a headless Chrome session for JS-rendered
                    content, infinite scroll, or pagination that requires
                    interaction.

A third "demo" mode generates realistic synthetic HTML-free data locally, so
the rest of the pipeline (parsing, cleaning, sentiment, viz) can be exercised
without making any network calls at all — useful for demos, interviews, or CI.
"""

import random
from dataclasses import dataclass, field
from typing import List

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from modules.utils import get_logger, polite_delay, random_user_agent, retry

logger = get_logger(__name__)

# Amazon serves pages over HTTPS; suppress noisy warnings if a proxy is used
# with an unverified certificate in a sandboxed dev environment.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class RawListing:
    """A single raw scraped record before parsing/cleaning."""
    title: str
    price_text: str
    rating_text: str
    review_count_text: str
    specs: dict = field(default_factory=dict)
    reviews: List[str] = field(default_factory=list)
    url: str = ""


class AmazonScraper:
    """Coordinates fetching search-result pages for a given query."""

    def __init__(self, engine: str = "requests"):
        self.engine = engine
        self.session = self._build_session()

    # ------------------------------------------------------------------ #
    # Session setup
    # ------------------------------------------------------------------ #
    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _headers(self) -> dict:
        headers = dict(config.DEFAULT_HEADERS)
        headers["User-Agent"] = random_user_agent()
        return headers

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def search(self, query: str, pages: int = 1) -> List[RawListing]:
        """Fetch `pages` worth of search results for `query` using the configured engine."""
        if self.engine == "requests":
            return self._search_with_requests(query, pages)
        if self.engine == "selenium":
            return self._search_with_selenium(query, pages)
        raise ValueError(f"Unknown engine: {self.engine}")

    # ------------------------------------------------------------------ #
    # requests + BeautifulSoup engine
    # ------------------------------------------------------------------ #
    @retry()
    def _fetch_page(self, url: str, params: dict) -> str:
        response = self.session.get(
            url, headers=self._headers(), params=params,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text

    def _search_with_requests(self, query: str, pages: int) -> List[RawListing]:
        listings: List[RawListing] = []
        for page_num in range(1, pages + 1):
            logger.info("Fetching page %d for query='%s' (requests engine)", page_num, query)
            try:
                html = self._fetch_page(
                    f"{config.BASE_URL}/s", {"k": query, "page": page_num}
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to fetch page %d after retries: %s", page_num, exc)
                continue

            listings.extend(self._parse_search_html(html))
            polite_delay()
        return listings

    def _parse_search_html(self, html: str) -> List[RawListing]:
        """Extract raw listing fields from a search-results page's HTML."""
        soup = BeautifulSoup(html, "lxml")
        results: List[RawListing] = []

        for card in soup.select("div[data-component-type='s-search-result']"):
            title_el = card.select_one("h2 span")
            price_el = card.select_one("span.a-price > span.a-offscreen")
            rating_el = card.select_one("span.a-icon-alt")
            review_count_el = card.select_one("span[aria-label$='ratings'], span.a-size-base")
            link_el = card.select_one("h2 a")

            results.append(
                RawListing(
                    title=title_el.get_text(strip=True) if title_el else "",
                    price_text=price_el.get_text(strip=True) if price_el else "",
                    rating_text=rating_el.get_text(strip=True) if rating_el else "",
                    review_count_text=(
                        review_count_el.get_text(strip=True) if review_count_el else ""
                    ),
                    url=(
                        f"{config.BASE_URL}{link_el['href']}"
                        if link_el and link_el.has_attr("href") else ""
                    ),
                )
            )
        return results

    # ------------------------------------------------------------------ #
    # Selenium engine (JS-rendered pages, infinite scroll, pagination)
    # ------------------------------------------------------------------ #
    def _search_with_selenium(self, query: str, pages: int) -> List[RawListing]:
        # Imported lazily so Selenium/webdriver-manager are only required
        # when this engine is actually selected.
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument(f"--user-agent={random_user_agent()}")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        listings: List[RawListing] = []
        try:
            for page_num in range(1, pages + 1):
                logger.info("Fetching page %d for query='%s' (selenium engine)", page_num, query)
                driver.get(f"{config.BASE_URL}/s?k={query}&page={page_num}")
                polite_delay()
                listings.extend(self._parse_search_html(driver.page_source))
        finally:
            driver.quit()
        return listings

    # ------------------------------------------------------------------ #
    # Offline / demo mode — synthetic data, zero network calls
    # ------------------------------------------------------------------ #
    def generate_demo_listings(self, query: str, count: int = 25) -> List[RawListing]:
        """Produce realistic synthetic listings so the pipeline can run end-to-end offline."""
        logger.info("Generating %d synthetic listings for demo mode (query='%s')", count, query)
        brands = ["Sony", "Anker", "JBL", "Bose", "Samsung", "Skullcandy", "Sennheiser", "Boat"]
        adjectives = ["Pro", "Max", "Lite", "2", "Plus", "Air", "Studio"]
        sample_reviews = [
            "Great sound quality and the battery lasts all day, very happy with this purchase.",
            "Comfortable fit but the bass feels a little weak compared to my old pair.",
            "Stopped connecting reliably after a few weeks, disappointed with the build quality.",
            "Excellent value for the price, works well for calls and music alike.",
            "Packaging was damaged on arrival but the product itself works fine so far.",
            "Noise cancellation is decent, not the best I've used but good for the price.",
        ]

        listings = []
        for i in range(count):
            brand = random.choice(brands)
            model = f"{brand} {query.title()} {random.choice(adjectives)}"
            price = round(random.uniform(15, 250), 2)
            rating = round(random.uniform(3.0, 5.0), 1)
            review_count = random.randint(5, 12000)
            reviews = random.sample(sample_reviews, k=random.randint(2, 4))

            listings.append(
                RawListing(
                    title=model,
                    price_text=f"${price}",
                    rating_text=f"{rating} out of 5 stars",
                    review_count_text=f"{review_count} ratings",
                    specs={
                        "Brand": brand,
                        "Connectivity": random.choice(["Bluetooth 5.0", "Bluetooth 5.3", "Wired"]),
                        "Battery Life": f"{random.randint(4, 40)} hours",
                    },
                    reviews=reviews,
                    url=f"{config.BASE_URL}/dp/DEMO{i:05d}",
                )
            )
        return listings
