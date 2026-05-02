"""
config.py – Central configuration for LinkedIn Auto Apply bot.
All sensitive values are loaded from a .env file or environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Chrome Profile
# ─────────────────────────────────────────────
# Path to the directory that CONTAINS your Chrome profiles (e.g. "Default", "Profile 1")
# macOS example:  /Users/yourname/Library/Application Support/Google/Chrome
# Linux example:  /home/yourname/.config/google-chrome
# Windows example: C:\Users\yourname\AppData\Local\Google\Chrome\User Data
CHROME_USER_DATA_DIR = os.getenv(
    "CHROME_USER_DATA_DIR",
    os.path.expanduser("~/.config/google-chrome"),   # Linux default
)

# The specific profile folder name inside CHROME_USER_DATA_DIR
CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR", "Default")

# ─────────────────────────────────────────────
# Job Search
# ─────────────────────────────────────────────
# Paste any LinkedIn jobs search URL with your filters already applied.
# The URL MUST contain "f_LF=f_AL" (Easy Apply filter) for best results.
LINKEDIN_JOBS_URL = os.getenv(
    "LINKEDIN_JOBS_URL",
    "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=Python%20Developer&location=India",
)

# Maximum number of job cards to attempt per run (set to 0 for unlimited)
MAX_APPLICATIONS = int(os.getenv("MAX_APPLICATIONS", 50))

# ─────────────────────────────────────────────
# Delays (seconds)
# ─────────────────────────────────────────────
DELAY_MIN = float(os.getenv("DELAY_MIN", 2))
DELAY_MAX = float(os.getenv("DELAY_MAX", 4))

# Implicit wait for Selenium element lookups (seconds)
IMPLICIT_WAIT = int(os.getenv("IMPLICIT_WAIT", 5))

# ─────────────────────────────────────────────
# Retry
# ─────────────────────────────────────────────
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# ─────────────────────────────────────────────
# Default Form Answers
# Edit these values — they are typed into any
# unfilled Easy Apply field automatically.
# ─────────────────────────────────────────────

DEFAULT_ANSWERS = {
    # ── Number / experience fields ───────────────
    "years_experience":        os.getenv("ANS_YEARS_EXP",        "5"),
    "years_experience_role":   os.getenv("ANS_YEARS_EXP_ROLE",   "5"),
    "years_experience_total":  os.getenv("ANS_YEARS_EXP_TOTAL",  "5"),

    # ── Salary / CTC ─────────────────────────────
    "salary_expected":         os.getenv("ANS_SALARY",           "1200000"),
    "ctc_expected":            os.getenv("ANS_CTC",              "1200000"),
    "current_ctc":             os.getenv("ANS_CURRENT_CTC",      "800000"),

    # ── Notice period ─────────────────────────────
    "notice_period":           os.getenv("ANS_NOTICE_PERIOD",    "30"),

    # ── URLs / links ──────────────────────────────
    "linkedin_profile":        os.getenv("ANS_LINKEDIN",         "https://www.linkedin.com/in/yourprofile"),
    "portfolio_url":           os.getenv("ANS_PORTFOLIO",        "https://github.com/yourusername"),
    "website_url":             os.getenv("ANS_WEBSITE",          "https://github.com/yourusername"),

    # ── Location / relocation ─────────────────────
    "city":                    os.getenv("ANS_CITY",             "Bengaluru"),
    "current_location":        os.getenv("ANS_LOCATION",         "Bengaluru, India"),

    # ── Generic fallback for any other text field ─
    "default_text":            os.getenv("ANS_DEFAULT_TEXT",     "5"),
    "default_number":          os.getenv("ANS_DEFAULT_NUMBER",   "5"),
}

# Keyword → answer key mapping.
# The bot reads each field's label, matches keywords below,
# and types the corresponding value from DEFAULT_ANSWERS.
FIELD_KEYWORD_MAP = [
    # (keyword_in_label_lowercase,   answer_key)
    ("years of experience",          "years_experience"),
    ("years experience",             "years_experience"),
    ("how many years",               "years_experience"),
    ("total experience",             "years_experience_total"),
    ("relevant experience",          "years_experience_role"),
    ("notice period",                "notice_period"),
    ("notice",                       "notice_period"),
    ("expected salary",              "salary_expected"),
    ("expected ctc",                 "ctc_expected"),
    ("current ctc",                  "current_ctc"),
    ("current salary",               "current_ctc"),
    ("linkedin",                     "linkedin_profile"),
    ("portfolio",                    "portfolio_url"),
    ("website",                      "website_url"),
    ("github",                       "portfolio_url"),
    ("city",                         "city"),
    ("location",                     "current_location"),
    ("current location",             "current_location"),
]

# ─────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CSV_FILE = os.path.join(DATA_DIR, "applications.csv")
LOG_FILE = os.path.join(LOGS_DIR, "bot.log")
