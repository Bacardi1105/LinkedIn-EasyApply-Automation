# 🤖 LinkedIn Easy Apply Bot

Tired of clicking "Easy Apply" a hundred times a day? Yeah, me too. This bot does it for you.

It opens LinkedIn, scrolls through job listings, clicks Easy Apply, fills in the forms with your default answers, and logs everything to a CSV so you know exactly what happened. You just watch it go (or don't — it runs on its own).

Built with Python + Selenium. No sketchy third-party services, no subscriptions, runs entirely on your machine.

---

## What it actually does

- Opens Chrome using **your existing profile** so it's already logged into LinkedIn
- Goes to whatever LinkedIn jobs URL you give it (with your filters already applied)
- For each job card it finds:
  - Checks if Easy Apply is available — skips if not
  - Clicks Easy Apply and handles the modal
  - **Fills in common fields automatically** — years of experience, notice period, salary, LinkedIn URL, relocation questions, yes/no dropdowns, etc.
  - If it hits a field it genuinely can't answer → skips that job and logs why
  - Submits and moves on
- Logs every single attempt to `data/applications.csv` with status: `applied`, `skipped`, or `error`
- Adds random delays between jobs so it doesn't look like a robot (well, it is one, but LinkedIn doesn't need to know that)

---

## Before you start

You need:

- **Python 3.8 or higher** — [download here](https://www.python.org/downloads/). During install, tick "Add Python to PATH"
- **Google Chrome** — already installed on most machines
- **A LinkedIn account** — obviously

That's it. ChromeDriver installs itself automatically.

---

## Setup (Windows)

**1. Download or clone this repo**

If you have Git:
```bash
git clone https://github.com/yourusername/linkedin-auto-apply.git
cd linkedin-auto-apply
```

Or just download the ZIP from GitHub and extract it somewhere.

**2. Open a terminal in the project folder**

Navigate to the folder in File Explorer, click the address bar, type `cmd` and hit Enter. That opens a terminal right there.

**3. Create a virtual environment and install dependencies**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

You should see `(venv)` at the start of your terminal line after the second command. That means it worked.

**4. Find your Chrome profile path**

Open Chrome and go to `chrome://version` in the address bar. Look for **Profile Path** — it'll look something like:

```
C:\Users\YourName\AppData\Local\Google\Chrome\User Data\Profile 1
```

You need two things from this:
- Everything before the last backslash → that's your `CHROME_USER_DATA_DIR`
- The last folder name (`Default`, `Profile 1`, `Profile 2`, etc.) → that's your `CHROME_PROFILE_DIR`

**5. Create your `.env` file**

```bash
copy .env.example .env
notepad .env
```

Fill it in with your actual values:

```env
CHROME_USER_DATA_DIR=C:\Users\YourName\AppData\Local\Google\Chrome\User Data
CHROME_PROFILE_DIR=Profile 1

LINKEDIN_JOBS_URL=https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=Software+Developer&location=India

MAX_APPLICATIONS=30
DELAY_MIN=2
DELAY_MAX=4
IMPLICIT_WAIT=5
MAX_RETRIES=3
```

**6. Update your default answers in `config.py`**

Open `config.py` and scroll down to the `DEFAULT_ANSWERS` section. Change these to your actual details:

```python
"years_experience":   "5",
"salary_expected":    "1200000",   # your expected CTC in rupees
"current_ctc":        "800000",    # your current CTC
"notice_period":      "30",        # in days
"linkedin_profile":   "https://www.linkedin.com/in/your-actual-profile",
"portfolio_url":      "https://github.com/your-actual-username",
"city":               "Bengaluru",
```

---

## How to build a good LinkedIn jobs URL

1. Go to [linkedin.com/jobs](https://www.linkedin.com/jobs/)
2. Search for your role and location
3. Click **Easy Apply** in the filters — this is important, otherwise the bot wastes time on jobs it can't apply to
4. Add any other filters you want (date posted, experience level, etc.)
5. Copy the full URL from your browser and paste it as `LINKEDIN_JOBS_URL` in your `.env`

---

## Running the bot

Every time you want to run it:

**Step 1 — Close all Chrome windows.** The bot needs exclusive access to your profile. If Chrome is already open, it'll crash.

```bash
taskkill /f /im chrome.exe
```

**Step 2 — Activate the virtual environment** (if you haven't already in this terminal session)

```bash
venv\Scripts\activate
```

**Step 3 — Run**

```bash
python main.py
```

Chrome will open, a pause prompt will appear in the terminal. Log into LinkedIn in the Chrome window if needed (first time only), then press Enter in the terminal to start.

After that it runs on its own. Watch the terminal to see what's happening in real time.

---

## Viewing your applications

There's a visual dashboard included — just open `view_applications.html` in any browser and drag your `data/applications.csv` onto it. You'll see a full breakdown of applied/skipped/error with search and filters.

The raw CSV is at `data/applications.csv` if you want to open it in Excel.

---

## Customising what the bot fills in

The bot matches field labels in forms to your answers using keyword matching. You can see and edit all of this in `config.py` under `FIELD_KEYWORD_MAP`. For example:

```python
("years of experience",   "years_experience"),
("notice period",         "notice_period"),
("expected salary",       "salary_expected"),
("linkedin",              "linkedin_profile"),
```

If the bot is skipping jobs because of a specific field you want it to handle, check what the field is called in the LinkedIn form and add a matching keyword here.

---

## Logs

Everything is logged to two places:

- **Terminal** — live output while the bot runs
- **`logs/bot.log`** — full session history, useful for debugging

Status meanings in the CSV:

| Status | Meaning |
|---|---|
| `applied` | Successfully submitted |
| `skipped` | No Easy Apply button, or a form field the bot couldn't fill |
| `error` | Something unexpected happened (modal didn't open, element not found, etc.) |

---

## Things that might go wrong

**"Chrome instance exited" or "DevTools port not found"**
Chrome was already open. Kill it with `taskkill /f /im chrome.exe` and try again.

**Bot opens Chrome but LinkedIn asks you to log in every time**
Your Chrome profile path is wrong. Double-check `CHROME_USER_DATA_DIR` and `CHROME_PROFILE_DIR` in `.env`. Go to `chrome://version` in Chrome to verify.

**Everything shows as "skipped"**
Two possible reasons: (1) your LinkedIn URL doesn't have the Easy Apply filter — make sure `f_LF=f_AL` or `f_AL=true` is in the URL, or (2) a form has a required field the bot can't fill — check the logs to see which field.

**"Unknown Title" and "Unknown Company" in the CSV**
LinkedIn updated their HTML. Open `bot/apply.py`, find the `SEL_JOB_TITLE` / `SEL_COMPANY` selectors and update the CSS class names to match what you see in Chrome DevTools on the job listing page.

**It's running slow**
Lower `DELAY_MIN` and `DELAY_MAX` in `config.py` or `.env`. Don't go below 1–2 seconds though — LinkedIn rate limits aggressively.

---

## Project structure

```
linkedin_auto_apply/
├── main.py              # Entry point
├── config.py            # All settings + your default form answers
├── .env                 # Your private config (not committed to git)
├── .env.example         # Template for .env
├── requirements.txt
├── view_applications.html  # Visual dashboard for your CSV
├── bot/
│   ├── driver.py        # Chrome setup
│   ├── apply.py         # Core apply logic + form filler
│   └── utils.py         # Helpers
├── data/
│   └── applications.csv # Auto-generated log
└── logs/
    └── bot.log          # Session logs
```

---

## ⚠️ Fair warning

Automating LinkedIn technically violates their Terms of Service. Your account could get restricted if you go too hard. Keep `MAX_APPLICATIONS` reasonable (30–50 per day max), don't run it 24/7, and keep an eye on what it's doing. This project is for educational purposes.

Also — **never commit your `.env` file to GitHub.** It's already in `.gitignore` but worth saying out loud. Your Chrome profile path is in there and you don't want that public.

---

## Contributing

PRs welcome. LinkedIn changes their HTML pretty regularly so selector fixes are always needed. If something breaks for you and you figure out the fix, open a PR.

---

*Built out of frustration with the LinkedIn job hunt. Good luck out there.*
