"""
bot/driver.py – Creates and configures the Selenium Chrome WebDriver.

Uses webdriver-manager to auto-download the correct ChromeDriver version.
Attaches to an existing Chrome profile so you stay logged in.
"""

import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import config

logger = logging.getLogger(__name__)

def build_options() -> Options:
    options = Options()

    options.add_argument(r"--user-data-dir=D:\latool\chrome_profile")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    logger.info("Using copied Chrome profile at D:\\latool\\chrome_profile")
    return options



def create_driver() -> webdriver.Chrome:
    """
    Instantiate and return a configured Chrome WebDriver.
    Raises RuntimeError if the driver cannot be created.
    """
    options = build_options()

    try:
        service = Service(r"C:\Users\Anshuman\.wdm\drivers\chromedriver\win64\147.0.7727.117\chromedriver-win32\chromedriver.exe")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as exc:
        raise RuntimeError(f"Failed to create Chrome WebDriver: {exc}") from exc

    # Patch navigator.webdriver to reduce bot fingerprint
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    driver.implicitly_wait(config.IMPLICIT_WAIT)
    logger.info("Chrome WebDriver created successfully.")
    return driver
