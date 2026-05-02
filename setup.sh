#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup.sh – One-shot setup and launcher for linkedin_auto_apply
#
# What it does:
#   1. Checks for Python 3.8+
#   2. Creates a virtual environment (venv/)
#   3. Installs requirements
#   4. Creates necessary folders and files
#   5. Prompts you to configure .env
#   6. Runs the bot
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e   # exit on first error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   LinkedIn Easy Apply Bot – Setup & Launch         ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Python version check ───────────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python || true)

if [ -z "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python 3 not found. Install Python 3.8+ and retry.${NC}"
    exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo -e "${RED}ERROR: Python 3.8+ required. Found $PY_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✔ Python $PY_VERSION detected.${NC}"

# ── 2. Virtual environment ────────────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment …"
    $PYTHON -m venv "$VENV_DIR"
    echo -e "${GREEN}✔ Virtual environment created at venv/${NC}"
else
    echo -e "${GREEN}✔ Virtual environment already exists.${NC}"
fi

# Activate
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows Git Bash
    # shellcheck disable=SC1091
    source "$VENV_DIR/Scripts/activate"
else
    echo -e "${RED}ERROR: Could not find venv activation script.${NC}"
    exit 1
fi

PIP="$VENV_DIR/bin/pip"
[ ! -f "$PIP" ] && PIP="$VENV_DIR/Scripts/pip"

# ── 3. Install requirements ───────────────────────────────────────────────────
echo ""
echo "Installing requirements …"
$PIP install --upgrade pip --quiet
$PIP install -r requirements.txt --quiet
echo -e "${GREEN}✔ Requirements installed.${NC}"

# ── 4. Create folders ─────────────────────────────────────────────────────────
mkdir -p data logs

if [ ! -f "data/applications.csv" ]; then
    echo "timestamp,job_title,company,location,job_url,status,notes" > data/applications.csv
    echo -e "${GREEN}✔ data/applications.csv created.${NC}"
fi

# ── 5. .env configuration ─────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}⚠  No .env file found.${NC}"
    echo "   Copying .env.example to .env …"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}   ACTION REQUIRED:${NC}"
    echo "   Edit .env and set:"
    echo "     • CHROME_USER_DATA_DIR  (path to your Chrome user data)"
    echo "     • LINKEDIN_JOBS_URL     (your filtered LinkedIn jobs URL)"
    echo ""
    echo "   Then re-run:  ./setup.sh"
    echo ""
    exit 0
else
    echo -e "${GREEN}✔ .env file found.${NC}"
fi

# ── 6. Run ────────────────────────────────────────────────────────────────────
PYTHON_VENV="$VENV_DIR/bin/python"
[ ! -f "$PYTHON_VENV" ] && PYTHON_VENV="$VENV_DIR/Scripts/python"

echo ""
echo -e "${GREEN}Launching bot …${NC}"
echo ""
$PYTHON_VENV main.py
