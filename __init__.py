"""
modules
-------
Core building blocks of the Amazon product intelligence pipeline:

    scraper.py         -> fetches raw product/review HTML or JSON
    parser.py           -> turns raw HTML into structured records
    data_cleaner.py      -> normalizes and validates records with Pandas
    review_analyzer.py   -> sentiment scoring on review text
    database.py           -> SQLite persistence for historical tracking
    visualizer.py          -> chart generation (Matplotlib / Plotly)
    utils.py                -> logging, retry decorator, shared helpers
"""
