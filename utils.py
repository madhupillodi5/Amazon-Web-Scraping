"""
utils.py
--------
Small, dependency-light helpers shared across the pipeline: logging setup,
a retry-with-backoff decorator, and a random-delay helper used to keep
scraping requests polite.
"""

import functools
import logging
import random
import time
from pathlib import Path

import config


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger that writes to both console and a log file."""
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid duplicate handlers on repeated calls
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    log_path = Path(config.LOG_DIR) / "pipeline.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def polite_delay(delay_range: tuple = config.REQUEST_DELAY_RANGE) -> None:
    """Sleep a randomized amount so requests don't hammer the target server."""
    time.sleep(random.uniform(*delay_range))


def retry(max_attempts: int = config.MAX_RETRIES, backoff: float = config.BACKOFF_FACTOR):
    """
    Decorator that retries a function on exception with exponential backoff.
    Logs each failed attempt; re-raises the final exception if all attempts fail.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch for retry
                    last_exc = exc
                    wait = backoff ** attempt
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s (retrying in %.1fs)",
                        attempt, max_attempts, func.__name__, exc, wait,
                    )
                    time.sleep(wait)
            logger.error("All %d attempts failed for %s", max_attempts, func.__name__)
            raise last_exc

        return wrapper

    return decorator


def random_user_agent() -> str:
    """Pick a random user agent string from the configured pool."""
    return random.choice(config.USER_AGENTS)
