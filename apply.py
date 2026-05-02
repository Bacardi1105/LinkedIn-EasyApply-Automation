"""
bot/apply.py – Core LinkedIn Easy Apply logic.

Flow per job card:
  1. Click the job card to load its details panel.
  2. Locate the "Easy Apply" button; skip if absent.
  3. Click Easy Apply → a modal opens.
  4. On each modal step:
       a. Fill any empty text/number inputs using DEFAULT_ANSWERS from config.
       b. Handle dropdowns (Yes/No, relocation, etc.)
       c. Handle radio buttons (Yes/No groups)
       d. If an unfillable required input remains → skip & log.
       e. Click Submit / Review / Next to advance.
  5. Log result to CSV.
"""

import logging
from typing import Optional, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

import config
from bot.utils import (
    click_element,
    find_element_safe,
    log_application,
    random_delay,
    retry,
    scroll_to_element,
    short_delay,
    wait_for_element,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Selectors
# ─────────────────────────────────────────────────────────────────────────────

SEL_JOB_CARDS       = (By.CSS_SELECTOR, "li.scaffold-layout__list-item")
SEL_EASY_APPLY_BTN  = (By.CSS_SELECTOR, "button.jobs-apply-button[aria-label*='Easy Apply']")
SEL_MODAL           = (By.CSS_SELECTOR, "div.jobs-easy-apply-modal")
SEL_SUBMIT_BTN      = (By.CSS_SELECTOR, "button[aria-label='Submit application']")
SEL_NEXT_BTN        = (By.CSS_SELECTOR, "button[aria-label='Continue to next step']")
SEL_REVIEW_BTN      = (By.CSS_SELECTOR, "button[aria-label='Review your application']")
SEL_CLOSE_BTN       = (By.CSS_SELECTOR, "button[aria-label='Dismiss']")
SEL_JOB_TITLE       = (By.CSS_SELECTOR, "h1.job-details-jobs-unified-top-card__job-title")
SEL_COMPANY         = (By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__company-name")
SEL_LOCATION        = (By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container")

MODAL_TEXT_INPUTS   = ("div.jobs-easy-apply-modal input[type='text']:not([disabled]),"
                       "div.jobs-easy-apply-modal input[type='number']:not([disabled])")
MODAL_TEXTAREAS     = "div.jobs-easy-apply-modal textarea:not([disabled])"
MODAL_SELECTS       = "div.jobs-easy-apply-modal select:not([disabled])"
MODAL_RADIO_GROUPS  = "div.jobs-easy-apply-modal fieldset"

# ─────────────────────────────────────────────────────────────────────────────
# Metadata helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_text(driver: WebDriver, selector: Tuple) -> str:
    el = find_element_safe(driver, *selector)
    return el.text.strip() if el else ""


def get_job_metadata(driver: WebDriver) -> Tuple[str, str, str]:
    return (
        _get_text(driver, SEL_JOB_TITLE),
        _get_text(driver, SEL_COMPANY),
        _get_text(driver, SEL_LOCATION),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Label detection
# ─────────────────────────────────────────────────────────────────────────────

def _get_field_label(driver: WebDriver, element: WebElement) -> str:
    """Try multiple strategies to read the label of a form field."""
    try:
        aria = (element.get_attribute("aria-label") or "").strip()
        if aria:
            return aria

        field_id = element.get_attribute("id")
        if field_id:
            lbl = find_element_safe(driver, By.CSS_SELECTOR, f"label[for='{field_id}']")
            if lbl:
                return lbl.text.strip()

        placeholder = (element.get_attribute("placeholder") or "").strip()
        if placeholder:
            return placeholder

        # Walk up DOM tree looking for a label or legend
        label_text = driver.execute_script("""
            let el = arguments[0];
            for (let i = 0; i < 6; i++) {
                el = el.parentElement;
                if (!el) break;
                let lbl = el.querySelector('label, legend');
                if (lbl && lbl.innerText.trim()) return lbl.innerText.trim();
            }
            return '';
        """, element)
        return (label_text or "").strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Answer resolver
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_answer(label_text: str, field_type: str = "text") -> str:
    """Match label keywords to a configured default answer."""
    label_lower = label_text.lower()
    for keyword, answer_key in config.FIELD_KEYWORD_MAP:
        if keyword in label_lower:
            val = config.DEFAULT_ANSWERS.get(answer_key, "")
            if val:
                return val
    return (config.DEFAULT_ANSWERS["default_number"]
            if field_type == "number"
            else config.DEFAULT_ANSWERS["default_text"])


# ─────────────────────────────────────────────────────────────────────────────
# Individual field fillers
# ─────────────────────────────────────────────────────────────────────────────

def _fill_text_input(driver: WebDriver, inp: WebElement) -> bool:
    try:
        if not inp.is_displayed():
            return False
        current_val = (inp.get_attribute("value") or "").strip()
        if current_val:
            return False  # already has a value, leave it

        field_type = inp.get_attribute("type") or "text"
        label      = _get_field_label(driver, inp)
        answer     = _resolve_answer(label, field_type)
        if not answer:
            return False

        scroll_to_element(driver, inp)
        inp.click()
        inp.clear()
        inp.send_keys(answer)
        short_delay()
        logger.info("  ✎ Filled [%s] '%s' → '%s'", field_type, label or "input", answer)
        return True
    except Exception as exc:
        logger.debug("_fill_text_input: %s", exc)
        return False


def _fill_textarea(driver: WebDriver, ta: WebElement) -> bool:
    try:
        if not ta.is_displayed():
            return False
        current_val = (ta.get_attribute("value") or ta.text or "").strip()
        if current_val:
            return False

        label  = _get_field_label(driver, ta)
        answer = _resolve_answer(label, "text")
        if not answer:
            return False

        scroll_to_element(driver, ta)
        ta.click()
        ta.clear()
        ta.send_keys(answer)
        short_delay()
        logger.info("  ✎ Filled textarea '%s'", label or "textarea")
        return True
    except Exception as exc:
        logger.debug("_fill_textarea: %s", exc)
        return False


def _fill_select(driver: WebDriver, sel_el: WebElement) -> bool:
    try:
        if not sel_el.is_displayed():
            return False
        select  = Select(sel_el)
        current = select.first_selected_option.text.strip().lower()
        if current and current not in ("select an option", "please select", "", "choose"):
            return False  # already selected

        label       = _get_field_label(driver, sel_el)
        label_lower = label.lower()

        # Yes/No or willingness → prefer Yes
        yes_keywords = ("relocat", "willing", "authoriz", "sponsor", "legally", "eligible")
        if any(k in label_lower for k in yes_keywords):
            for opt in select.options:
                if opt.text.strip().lower() in ("yes", "i am", "i do", "willing", "true"):
                    select.select_by_visible_text(opt.text.strip())
                    logger.info("  ✎ Select '%s' → '%s'", label, opt.text.strip())
                    short_delay()
                    return True

        # Generic: first real option
        for opt in select.options:
            text = opt.text.strip()
            if text and text.lower() not in ("select an option", "please select", "", "choose"):
                select.select_by_visible_text(text)
                logger.info("  ✎ Select '%s' → '%s'", label, text)
                short_delay()
                return True
        return False
    except Exception as exc:
        logger.debug("_fill_select: %s", exc)
        return False


def _fill_radio_group(driver: WebDriver, fieldset: WebElement) -> bool:
    try:
        if not fieldset.is_displayed():
            return False
        radios = fieldset.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        if not radios:
            return False
        if any(r.is_selected() for r in radios):
            return False  # already answered

        legend = ""
        try:
            legend = fieldset.find_element(By.TAG_NAME, "legend").text.strip()
        except Exception:
            pass

        # Prefer "Yes" option
        for radio in radios:
            lbl = _get_field_label(driver, radio).lower()
            if lbl in ("yes", "i am", "i do", "willing", "true"):
                scroll_to_element(driver, radio)
                click_element(driver, radio)
                logger.info("  ✎ Radio '%s' → Yes", legend or "group")
                short_delay()
                return True

        # Fallback: first option
        scroll_to_element(driver, radios[0])
        click_element(driver, radios[0])
        first_lbl = _get_field_label(driver, radios[0])
        logger.info("  ✎ Radio '%s' → '%s' (first)", legend or "group", first_lbl)
        short_delay()
        return True
    except Exception as exc:
        logger.debug("_fill_radio_group: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Step-level form filler
# ─────────────────────────────────────────────────────────────────────────────

def fill_form_fields(driver: WebDriver) -> bool:
    """
    Fill all visible unfilled fields on the current modal step.
    Returns True if everything was handled, False if an unfillable field remains.
    """
    short_delay()
    any_unfillable = False

    # Text / number inputs
    try:
        for inp in driver.find_elements(By.CSS_SELECTOR, MODAL_TEXT_INPUTS):
            if not inp.is_displayed():
                continue
            if (inp.get_attribute("value") or "").strip():
                continue  # already filled
            filled = _fill_text_input(driver, inp)
            if not filled:
                label = _get_field_label(driver, inp)
                logger.warning("  ⚠ Could not fill: '%s'", label or "text input")
                any_unfillable = True
    except Exception as exc:
        logger.debug("Text scan error: %s", exc)

    # Textareas
    try:
        for ta in driver.find_elements(By.CSS_SELECTOR, MODAL_TEXTAREAS):
            if not ta.is_displayed():
                continue
            if (ta.get_attribute("value") or ta.text or "").strip():
                continue
            filled = _fill_textarea(driver, ta)
            if not filled:
                any_unfillable = True
    except Exception as exc:
        logger.debug("Textarea scan error: %s", exc)

    # Selects
    try:
        for sel_el in driver.find_elements(By.CSS_SELECTOR, MODAL_SELECTS):
            _fill_select(driver, sel_el)
    except Exception as exc:
        logger.debug("Select scan error: %s", exc)

    # Radio groups
    try:
        for fs in driver.find_elements(By.CSS_SELECTOR, MODAL_RADIO_GROUPS):
            _fill_radio_group(driver, fs)
    except Exception as exc:
        logger.debug("Radio scan error: %s", exc)

    return not any_unfillable


def _has_unfilled_required(driver: WebDriver) -> bool:
    """Final guard: check required fields are not still empty."""
    try:
        required = driver.find_elements(
            By.CSS_SELECTOR,
            "div.jobs-easy-apply-modal input[required]:not([disabled]),"
            "div.jobs-easy-apply-modal textarea[required]:not([disabled])",
        )
        for inp in required:
            if inp.is_displayed():
                val = (inp.get_attribute("value") or inp.text or "").strip()
                if not val:
                    label = _get_field_label(driver, inp)
                    logger.warning("  ⚠ Required field still empty: '%s'", label or "unknown")
                    return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Modal close
# ─────────────────────────────────────────────────────────────────────────────

def _close_modal(driver: WebDriver) -> None:
    close_btn = find_element_safe(driver, *SEL_CLOSE_BTN)
    if close_btn:
        click_element(driver, close_btn)
        short_delay()
        discard_btn = wait_for_element(
            driver, By.CSS_SELECTOR,
            "button[data-control-name='discard_application_confirm_btn']",
            timeout=3, clickable=True,
        )
        if discard_btn:
            click_element(driver, discard_btn)
        short_delay()


# ─────────────────────────────────────────────────────────────────────────────
# Modal navigation
# ─────────────────────────────────────────────────────────────────────────────

def _navigate_modal(driver: WebDriver) -> str:
    """Step through the Easy Apply modal, filling fields at each step."""
    MAX_STEPS = 10

    for step in range(MAX_STEPS):
        logger.debug("Modal step %d", step + 1)
        short_delay()

        # Fill everything on this page
        all_filled = fill_form_fields(driver)

        # Bail if a required field is still empty after filling
        if not all_filled or _has_unfilled_required(driver):
            logger.info("  ↳ Unfillable required field on step %d – skipping.", step + 1)
            _close_modal(driver)
            return "skipped"

        # Submit?
        submit = wait_for_element(driver, *SEL_SUBMIT_BTN, timeout=3, clickable=True)
        if submit and submit.is_displayed():
            logger.info("  ↳ Submitting on step %d.", step + 1)
            click_element(driver, submit)
            short_delay()
            return "submitted"

        # Review?
        review = wait_for_element(driver, *SEL_REVIEW_BTN, timeout=2, clickable=True)
        if review and review.is_displayed():
            click_element(driver, review)
            short_delay()
            continue

        # Next?
        nxt = wait_for_element(driver, *SEL_NEXT_BTN, timeout=2, clickable=True)
        if nxt and nxt.is_displayed():
            click_element(driver, nxt)
            short_delay()
            continue

        logger.warning("  ↳ No actionable button on step %d.", step + 1)
        _close_modal(driver)
        return "error"

    logger.error("  ↳ Exceeded max steps.")
    _close_modal(driver)
    return "error"


# ─────────────────────────────────────────────────────────────────────────────
# Per-job apply
# ─────────────────────────────────────────────────────────────────────────────

def apply_to_job(driver: WebDriver, card: WebElement) -> None:
    job_url = driver.current_url

    try:
        scroll_to_element(driver, card)
        click_element(driver, card)
        random_delay(1, 2)

        job_url = driver.current_url
        title, company, location = get_job_metadata(driver)
        logger.info("Checking: %s @ %s", title or "Unknown Title", company or "Unknown Company")

        easy_apply_btn = wait_for_element(driver, *SEL_EASY_APPLY_BTN, timeout=5, clickable=True)
        if not easy_apply_btn:
            logger.info("  → No Easy Apply – skipping.")
            log_application(config.CSV_FILE, title, company, location, job_url, "skipped", "No Easy Apply button")
            return

        click_element(driver, easy_apply_btn)
        short_delay()

        modal = wait_for_element(driver, *SEL_MODAL, timeout=6)
        if not modal:
            logger.warning("  → Modal did not open.")
            log_application(config.CSV_FILE, title, company, location, job_url, "error", "Modal did not open")
            return

        outcome = _navigate_modal(driver)
        status  = {"submitted": "applied", "skipped": "skipped", "error": "error"}.get(outcome, "error")
        notes   = {"applied": "", "skipped": "Unfillable field", "error": "Navigation failed"}.get(status, "")

        log_application(config.CSV_FILE, title, company, location, job_url, status, notes)
        logger.info("  → Result: %s", status.upper())

    except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as exc:
        logger.error("apply_to_job error: %s", exc)
        try:
            _close_modal(driver)
        except Exception:
            pass
        log_application(config.CSV_FILE, "", "", "", job_url, "error", str(exc))

    finally:
        random_delay()


# ─────────────────────────────────────────────────────────────────────────────
# Page orchestration
# ─────────────────────────────────────────────────────────────────────────────

def load_jobs_page(driver: WebDriver, url: str) -> None:
    logger.info("Loading jobs page: %s", url)
    driver.get(url)
    random_delay(3, 5)


def get_job_cards(driver: WebDriver):
    try:
        return driver.find_elements(*SEL_JOB_CARDS)
    except Exception as exc:
        logger.error("Could not retrieve job cards: %s", exc)
        return []


def run_apply_loop(driver: WebDriver) -> None:
    from bot.utils import ensure_csv
    ensure_csv(config.CSV_FILE)
    load_jobs_page(driver, config.LINKEDIN_JOBS_URL)

    cards = get_job_cards(driver)
    total = len(cards)
    logger.info("Found %d job card(s) on page.", total)

    limit         = config.MAX_APPLICATIONS if config.MAX_APPLICATIONS > 0 else total
    applied_count = 0

    for idx, card in enumerate(cards[:limit], start=1):
        logger.info("─── Job %d / %d ───────────────────────────────", idx, min(limit, total))
        try:
            apply_to_job(driver, card)
            applied_count += 1
        except Exception as exc:
            logger.exception("Unexpected error on job %d: %s", idx, exc)

    logger.info("Session complete. Processed %d job(s). See %s", applied_count, config.CSV_FILE)
