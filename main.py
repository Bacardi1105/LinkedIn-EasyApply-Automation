"""
main.py – Entry point for the LinkedIn Easy Apply bot.

Usage:
    python main.py

All configuration is handled via config.py / .env file.
"""

import logging
import os
import sys

import config
from bot.apply import run_apply_loop
from bot.driver import create_driver
from bot.utils import ensure_csv


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure root logger to write to both console and a rotating log file."""
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    fmt = "%(asctime)s  %(levelname)-8s  %(name)s – %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )

    # Suppress noisy third-party loggers
    for noisy in ("selenium", "urllib3", "WDM"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────

def preflight_checks() -> None:
    """Warn the user about common mis-configurations before starting."""
    issues = []

    if "linkedin.com/jobs" not in config.LINKEDIN_JOBS_URL:
        issues.append(
            "LINKEDIN_JOBS_URL does not look like a LinkedIn jobs URL. "
            "Set it in .env or config.py."
        )

    if not os.path.isdir(config.CHROME_USER_DATA_DIR):
        issues.append(
            f"CHROME_USER_DATA_DIR not found: {config.CHROME_USER_DATA_DIR}\n"
            "  → Update CHROME_USER_DATA_DIR in .env / config.py so the bot "
            "can re-use your logged-in Chrome profile."
        )

    if issues:
        logger.warning("─── Pre-flight warnings ─────────────────────────────")
        for i, issue in enumerate(issues, 1):
            logger.warning("%d. %s", i, issue)
        logger.warning("─────────────────────────────────────────────────────")
        logger.warning(
            "The bot will still run, but may prompt for LinkedIn login "
            "or apply to wrong jobs."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    setup_logging()
    logger.info("═══════════════════════════════════════════════════")
    logger.info("   LinkedIn Easy Apply Bot  –  starting up")
    logger.info("═══════════════════════════════════════════════════")
    preflight_checks()

    os.makedirs(config.DATA_DIR, exist_ok=True)
    ensure_csv(config.CSV_FILE)

    driver = None
    try:
        driver = create_driver()
        input(">>> Log into LinkedIn in the Chrome window, then press ENTER here to start the bot...")
        run_apply_loop(driver)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except RuntimeError as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unhandled exception: %s", exc)
        sys.exit(1)
    finally:
        if driver:
            logger.info("Closing browser …")
            driver.quit()
        logger.info("Bot session ended.")


if __name__ == "__main__":
    main()
