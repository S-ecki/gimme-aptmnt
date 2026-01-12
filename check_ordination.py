import re
import sys
import datetime as dt
from zoneinfo import ZoneInfo
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

URL = "https://home.cgm-life.de/eservices/#/appointment/?institution=48c93e67-2172-4c0a-967a-a474a0bb44a4"
TZ = ZoneInfo("Europe/Vienna")
THRESHOLD_DAY = 27
THRESHOLD_MONTH = 2  # February
NTFY_TOPIC = "gimme-aptmnt-secki"

RE_DDMM = re.compile(r"(\d{2})\.(\d{2})\.")
RE_WEEK = re.compile(r"(?:Week|Woche)\s+(\d{2})\.(\d{2})\.\-\s*(\d{2})\.(\d{2})\.(\d{4})", re.I)
RE_TIME = re.compile(r"^(\d{1,2}):(\d{2})$")


def accept_cookies_best_effort(page) -> None:
    for name in ["Alle akzeptieren", "Akzeptieren", "Zustimmen", "OK"]:
        try:
            btn = page.get_by_role("button", name=re.compile(fr"^{re.escape(name)}$", re.I))
            if btn.count() > 0:
                btn.first.click(timeout=1500)
                return
        except Exception:
            pass


def select_ordination(page) -> None:
    box = page.locator('[data-testid="appointmentTypeCombobox"]')
    box.wait_for(state="visible", timeout=60_000)

    # Open dropdown
    box.locator('[data-testid="dropdown_button"]').click(timeout=10_000)

    # Click the "Ordination" entry (exact match to avoid "private Ordination")
    entries = box.locator('[data-testid="dropdown_entry"]')
    target = entries.filter(has_text=re.compile(r"^\s*Ordination\s*$"))
    target.first.click(timeout=10_000)


def trigger_action(appointment_date: dt.datetime) -> None:
    """Send notification via ntfy.sh with the appointment date."""
    date_str = appointment_date.strftime("%d.%m %H:%M")
    message = f"Appointment available {date_str}"
    
    try:
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": "HOLUP",
                "Priority": "high",
            },
            timeout=10,
        )
        response.raise_for_status()
    except Exception as e:
        # Don't fail the script if notification fails
        print(f"WARNING: Failed to send notification: {e}", file=sys.stderr)


def extract_soonest_datetime_from_calendar(page) -> dt.datetime:
    cal = page.locator('[data-testid="appointmentBookingCalendar"]')
    cal.wait_for(state="visible", timeout=60_000)

    # Wait a moment for the calendar to refresh after selecting "Ordination"
    page.wait_for_timeout(500)

    # Header like: "Week 15.06.-21.06.2026"
    header = cal.locator("thead.calendar-header").inner_text().strip()
    m = RE_WEEK.search(header)
    if not m:
        raise RuntimeError(f"Could not parse week header: {header!r}")

    start_d, start_m, end_d, end_m, year = map(int, m.groups())
    start_month = start_m

    # Day headers: "Mo.\n15.06." etc (no year shown there)
    day_ps = cal.locator("thead").nth(1).locator("th p.smalltxt")
    if day_ps.count() < 7:
        raise RuntimeError("Could not read 7 day columns from the calendar header.")

    # Handle year crossing (e.g. Dec -> Jan) just in case:
    def make_date(dd: int, mm: int) -> dt.date:
        y = year
        if mm < start_month:  # likely crossed into Jan of next year
            y = year + 1
        return dt.date(y, mm, dd)

    day_dates: list[dt.date] = []
    for i in range(7):
        txt = day_ps.nth(i).inner_text().strip()
        dm = RE_DDMM.search(txt)
        if not dm:
            raise RuntimeError(f"Could not parse day header date from: {txt!r}")
        dd, mm = map(int, dm.groups())
        day_dates.append(make_date(dd, mm))

    now = dt.datetime.now(TZ)

    rows = cal.locator("tbody tr.calendar_row")
    best: dt.datetime | None = None

    for r in range(rows.count()):
        row = rows.nth(r)
        tds = row.locator("td")
        col_count = min(7, tds.count())
        for c in range(col_count):
            a = tds.nth(c).locator("a").first
            time_txt = a.inner_text().strip()
            if not time_txt:
                continue
            tm = RE_TIME.match(time_txt)
            if not tm:
                continue
            hh, mi = map(int, tm.groups())
            candidate = dt.datetime.combine(day_dates[c], dt.time(hh, mi), tzinfo=TZ)
            if candidate >= now and (best is None or candidate < best):
                best = candidate

    if best is None:
        raise RuntimeError("No available appointment times found in the currently displayed calendar.")
    return best


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="de-AT", timezone_id="Europe/Vienna")
        page = context.new_page()

        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        accept_cookies_best_effort(page)

        select_ordination(page)

        soonest = extract_soonest_datetime_from_calendar(page)
        print(soonest.strftime("%Y-%m-%d %H:%M"))

        # Only send notification if appointment is before threshold date (February 27th)
        threshold_date = dt.date(soonest.year, THRESHOLD_MONTH, THRESHOLD_DAY)
        if soonest.date() < threshold_date:
            trigger_action(soonest)

        browser.close()


if __name__ == "__main__":
    try:
        main()
    except PWTimeoutError as e:
        print(f"ERROR: Timeout: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
