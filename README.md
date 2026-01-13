# Appointment Checker

## Docker (Recommended)

```bash
docker build -t appointment-checker .
docker run --rm appointment-checker
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
