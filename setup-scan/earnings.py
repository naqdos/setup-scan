"""
Pulls the FULL market's earnings calendar (not filtered to any watchlist)
for the current business week, grouped by day and by session
(before-open / after-close). Fetches all 5 weekdays in parallel.
"""
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

NASDAQ_URL = "https://api.nasdaq.com/api/calendar/earnings"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fetch_day(date_str):
    """Returns the list of ticker rows reporting on this date, or [] on failure."""
    try:
        resp = requests.get(NASDAQ_URL, params={"date": date_str}, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("data") or {}).get("rows") or []
    except Exception:
        return []


def _session_bucket(time_value):
    """Nasdaq's 'time' field -> 'before_open' / 'after_close' / 'other'."""
    t = (time_value or "").lower()
    if "pre" in t or "before" in t:
        return "before_open"
    if "after" in t:
        return "after_close"
    return "other"


def _week_dates():
    """Monday-Friday of the current business week (next week's if it's a weekend)."""
    today = datetime.now().date()
    weekday = today.weekday()  # Mon=0 ... Sun=6
    if weekday >= 5:
        monday = today + timedelta(days=(7 - weekday))
    else:
        monday = today - timedelta(days=weekday)
    return [monday + timedelta(days=i) for i in range(5)]


def get_week_earnings():
    """
    Returns:
    {
      "dates": ["2026-08-03", ...],  # Mon..Fri
      "days": {
        "2026-08-03": {"before_open": [...], "after_close": [...], "other": [...]},
        ...
      }
    }
    Each entry in a bucket is {"ticker": ..., "name": ..., "eps_forecast": ...}.
    """
    dates = _week_dates()
    date_strs = [d.isoformat() for d in dates]

    with ThreadPoolExecutor(max_workers=5) as executor:
        all_rows = list(executor.map(_fetch_day, date_strs))

    days = {}
    for date_str, rows in zip(date_strs, all_rows):
        buckets = {"before_open": [], "after_close": [], "other": []}
        for row in rows:
            symbol = (row.get("symbol") or "").upper()
            if not symbol:
                continue
            entry = {
                "ticker": symbol,
                "name": row.get("name"),
                "eps_forecast": row.get("epsForecast"),
            }
            buckets[_session_bucket(row.get("time"))].append(entry)
        days[date_str] = buckets

    return {"dates": date_strs, "days": days}


# Kept for anything still calling the old per-watchlist signature.
def get_upcoming_earnings(tickers=None, days=7):
    from scan import DEFAULT_SCAN_LIST
    watch = set(t.upper() for t in (tickers or DEFAULT_SCAN_LIST))
    week = get_week_earnings()
    results = []
    today = datetime.now().date()
    for date_str, buckets in week["days"].items():
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_away = (d - today).days
        for bucket in buckets.values():
            for entry in bucket:
                if entry["ticker"] in watch:
                    results.append({**entry, "earnings_date": date_str, "days_away": days_away})
    results.sort(key=lambda r: r["days_away"])
    return results
