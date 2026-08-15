# 🛒 Amazon Product Intelligence & Competitive Benchmarking Dashboard

A modular data pipeline that extracts product data (pricing, specs, ratings, and reviews) from
Amazon listings, cleans and enriches it, and turns it into interactive dashboards for
competitive benchmarking and price-trend tracking.

> Built as a personal data engineering / analytics project to demonstrate end-to-end skills in
> web scraping, ETL pipeline design, sentiment analysis, and data visualization.

---

## Features

- **Multi-strategy scraping engine** — `requests` + `BeautifulSoup` for lightweight static
  pages, with a `Selenium` fallback for JS-rendered content and pagination.
- **Resilient by design** — rotating user agents, randomized request delays, retry-with-backoff,
  and structured logging so a single failed request never kills the pipeline.
- **ETL-style cleaning pipeline** — Pandas-based normalization of price strings, star ratings,
  review counts, and duplicate/missing-value handling.
- **Review sentiment analysis** *(new)* — scores customer reviews with TextBlob/VADER to surface
  overall sentiment per product, not just star ratings.
- **Historical price tracking** *(new)* — persists snapshots to a local SQLite database so price
  trends can be tracked run-over-run, not just as a single snapshot.
- **Static + interactive dashboards** — Matplotlib/Seaborn charts for reports, and an optional
  Streamlit dashboard *(new)* for live, filterable competitive benchmarking.
- **Config-driven** — all scraping targets, delays, and output paths live in `config.py`, no
  hard-coded values scattered across modules.
- **Demo/offline mode** *(new)* — a built-in synthetic data generator lets the full pipeline run
  and be demoed end-to-end without hitting a live site, useful for CI, interviews, or portfolio
  demos.

---

## Project Structure

```
amazon-scraper-analytics/
├── main.py                    # Orchestrator – runs the full pipeline end-to-end
├── dashboard.py                # Streamlit interactive dashboard entry point
├── config.py                   # Central configuration (paths, headers, delays, DB)
├── requirements.txt
├── .gitignore
├── modules/
│   ├── __init__.py
│   ├── utils.py                 # Logging setup, retry decorator, helpers
│   ├── scraper.py                # AmazonScraper – requests/BS4 + Selenium fallback
│   ├── parser.py                  # Raw HTML -> structured product records
│   ├── data_cleaner.py            # Pandas cleaning & normalization pipeline
│   ├── review_analyzer.py         # Sentiment scoring on review text
│   ├── database.py                # SQLite persistence + price-history queries
│   └── visualizer.py              # Matplotlib/Plotly chart generation
└── data/
    ├── raw/                     # Raw scraped/generated JSON snapshots
    ├── processed/                # Cleaned CSV outputs
    └── db/                       # SQLite database file
```

---

## Installation

```bash
git clone https://github.com/<your-username>/amazon-scraper-analytics.git
cd amazon-scraper-analytics
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Selenium mode additionally requires a matching browser driver (e.g. `chromedriver`) available
on your `PATH`, or use `webdriver-manager` (already included in `requirements.txt`).

---

## Usage

### Run the full pipeline (scrape → clean → analyze → visualize)

```bash
python main.py --query "wireless earbuds" --pages 2
```

### Run in offline/demo mode (no network calls, synthetic data)

```bash
python main.py --query "wireless earbuds" --demo
```

### Launch the interactive dashboard

```bash
streamlit run dashboard.py
```

### CLI options

| Flag         | Description                                      | Default |
|--------------|---------------------------------------------------|---------|
| `--query`    | Search term to benchmark                          | required|
| `--pages`    | Number of result pages to pull                     | `1`     |
| `--engine`   | `requests` or `selenium`                           | `requests` |
| `--demo`     | Run entirely on synthetic data (no scraping)       | `False` |
| `--no-viz`   | Skip chart generation                              | `False` |

---

## Sample Output

Running the pipeline produces:

- `data/processed/<query>_clean.csv` — cleaned, structured product table
- `data/db/amazon_products.sqlite` — historical snapshots for trend analysis
- `data/processed/charts/` — PNG charts: price distribution, price-vs-rating,
  brand comparison, sentiment breakdown, price trend over time

---

## ⚠️ Important: Compliance Note

Amazon's [Conditions of Use](https://www.amazon.com/gp/help/customer/display.html) restrict
automated data collection from its site. This project is intended for **educational and
portfolio purposes**. Before running the live scraper against any real site:

- Review and respect that site's `robots.txt` and Terms of Service.
- Prefer official, sanctioned APIs where available (e.g. the
  [Amazon Product Advertising API](https://webservices.amazon.com/paapi5/documentation/)) for
  any production or commercial use case.
- Use conservative request rates and caching to avoid placing load on the target site.

The `--demo` flag exists specifically so the whole pipeline can be explored and showcased
without scraping a live page.

---

## Tech Stack

`Python` · `Selenium` · `Scrapy-style parsing utilities` · `BeautifulSoup4` · `Urllib3` ·
`Pandas` · `Matplotlib` · `Seaborn` · `Plotly` · `Streamlit` · `SQLite` · `TextBlob`

---

## License

MIT — see `LICENSE`.
