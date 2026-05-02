"""
bot/utils.py – Shared helpers: waiting, retrying, CSV logging, random delays.
"""

import csv
import logging
import os
import random
import time
from datetime import datetime
from functools import wraps
from typing import Callable, Optional, TypeVar

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)

# ─────────────────────────────────────────────────────────────────────────────
# Delay helpers
# ─────────────────────────────────────────────────────────────────────────────

def random_delay(min_sec: float = None, max_sec: float = None) -> None:
    """Sleep for a random duration between min_sec and max_sec."""
    lo = min_sec if min_sec is not None else config.DELAY_MIN
    hi = max_sec if max_sec is not None else config.DELAY_MAX
    duration = random.uniform(lo, hi)
    logger.debug("Sleeping %.2f seconds …", duration)
    time.sleep(duration)


def short_delay() -> None:
    """Quick pause (0.5–1.5 s) for UI interactions."""
    random_delay(0.5, 1.5)


# ─────────────────────────────────────────────────────────────────────────────
# Retry decorator
# ─────────────────────────────────────────────────────────────────────────────

def retry(max_attempts: int = None, delay: float = 2.0, exceptions=(Exception,)):
    """
    Decorator: retry a function up to *max_attempts* times on specified exceptions.
    Falls back to config.MAX_RETRIES when max_attempts is None.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = max_attempts if max_attempts is not None else config.MAX_RETRIES
            last_exc: Optional[Exception] = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    logger.warning(
                        "[%s] Attempt %d/%d failed: %s",
                        func.__name__, attempt, attempts, exc,
                    )
                    if attempt < attempts:
                        time.sleep(delay)
            raise last_exc  # re-raise after all attempts exhausted
        return wrapper  # type: ignore[return-value]
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Element helpers
# ─────────────────────────────────────────────────────────────────────────────

def wait_for_element(
    driver: WebDriver,
    by: str,
    value: str,
    timeout: int = 10,
    clickable: bool = False,
) -> Optional[WebElement]:
    """
    Wait until an element is present (or clickable) and return it.
    Returns None on timeout instead of raising.
    """
    condition = (
        EC.element_to_be_clickable((by, value))
        if clickable
        else EC.presence_of_element_located((by, value))
    )
    try:
        return WebDriverWait(driver, timeout).until(condition)
    except TimeoutException:
        logger.debug("Timed out waiting for element: [%s] %s", by, value)
        return None


def find_element_safe(
    driver: WebDriver,
    by: str,
    value: str,
) -> Optional[WebElement]:
    """Return an element or None (never raises)."""
    try:
        return driver.find_element(by, value)
    except (NoSuchElementException, StaleElementReferenceException):
        return None


def click_element(
    driver: WebDriver,
    element: WebElement,
) -> bool:
    """
    Try a normal click; fall back to JavaScript click.
    Returns True on success.
    """
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as exc:
            logger.debug("click_element failed: %s", exc)
            return False


def has_visible_text_inputs(driver: WebDriver) -> bool:
    """
    Return True if the currently visible modal/form contains unfilled
    text or textarea inputs (signals a complex form we should skip).
    """
    try:
        inputs = driver.find_elements(
            By.CSS_SELECTOR,
            "div.jobs-easy-apply-modal input[type='text']:not([disabled]), "
            "div.jobs-easy-apply-modal textarea:not([disabled])",
        )
        for inp in inputs:
            if inp.is_displayed() and not inp.get_attribute("value").strip():
                return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Scroll helpers
# ─────────────────────────────────────────────────────────────────────────────

def scroll_to_element(driver: WebDriver, element: WebElement) -> None:
    """Scroll the element into view."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    short_delay()


def scroll_down_page(driver: WebDriver, pixels: int = 800) -> None:
    """Scroll the page down by *pixels*."""
    driver.execute_script(f"window.scrollBy(0, {pixels});")
    short_delay()


# ─────────────────────────────────────────────────────────────────────────────
# CSV logging
# ─────────────────────────────────────────────────────────────────────────────

CSV_HEADERS = [
    "timestamp",
    "job_title",
    "company",
    "location",
    "job_url",
    "status",
    "notes",
]


def ensure_csv(filepath: str) -> None:
    """Create the CSV with headers if it doesn't already exist."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.isfile(filepath):
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
            writer.writeheader()
        logger.info("Created CSV log: %s", filepath)


def log_application(
    filepath: str,
    job_title: str,
    company: str,
    location: str,
    job_url: str,
    status: str,
    notes: str = "",
) -> None:
    """Append one row to the applications CSV."""
    ensure_csv(filepath)
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "job_title": job_title,
        "company": company,
        "location": location,
        "job_url": job_url,
        "status": status,
        "notes": notes,
    }
    with open(filepath, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADERS)
        writer.writerow(row)
    logger.debug("CSV logged [%s] %s @ %s – %s", status, job_title, company, notes)
