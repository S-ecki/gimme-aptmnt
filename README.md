# Appointment Checker

Checks the earliest available appointment for a dermatologist on CGM Life's eServices booking page and sends notifications via ntfy.sh.

## GitHub Actions (Free Hosting)

**Setup:**
1. Push this repository to GitHub
2. Go to repository → Actions tab
3. The workflow will automatically run hourly
4. You can also trigger manually via "Run workflow" button

The workflow runs every hour and sends notifications if an appointment before February 27th is found.

## Docker (Recommended)

```bash
docker build -t appointment-checker .
docker run --rm appointment-checker
```

**Schedule on remote server:**
```bash
# Cron (every hour)
0 * * * * docker run --rm appointment-checker >> /var/log/appointment-checker.log 2>&1
```

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
python3 check_ordination.py
```

## Output

Format: `YYYY-MM-DD HH:MM` (e.g., `2026-06-18 13:30`)
