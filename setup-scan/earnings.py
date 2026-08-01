"""
Pulls the market's earnings calendar for the current business week, grouped
by day and session (before-open / after-close). Filters to companies with
market cap >= $500M and caps each session at 15 names, largest cap first,
since the unfiltered list runs into the hundreds and most are illiquid names
nobody's tracking.
"""
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

NASDAQ_URL = "https://api.nasdaq.com/api/calendar/earnings"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

MIN_MARKET_CAP = 500_000_000
MAX_PER_SESSION = 15


def _fetch_day(date_str):
    """Returns the list of ticker rows reporting on this date, or [] on failure."""
    try:
        resp = requests.get(NASDAQ_URL, params={"date": date_str}, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("data") or {}).get("rows") or []
    except Exception:
        return []


def _parse_market_cap(value):
    """Nasdaq returns this as a string like '$1,234,567,890' or 'NA'."""
    if not value:
        return None
    s = str(value).replace("$", "").replace(",", "").strip()
    if not s or s.upper() in ("N/A", "NA"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _format_market_cap(value):
    if value is None:
        return None
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"


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
    Each bucket holds at most MAX_PER_SESSION entries, filtered to market cap
    >= MIN_MARKET_CAP, sorted largest-cap first.
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
            cap = _parse_market_cap(row.get("marketCap"))
            if cap is None or cap < MIN_MARKET_CAP:
                continue
            entry = {
                "ticker": symbol,
                "name": row.get("name"),
                "eps_forecast": row.get("epsForecast"),
                "market_cap": cap,
                "market_cap_formatted": _format_market_cap(cap),
            }
            buckets[_session_bucket(row.get("time"))].append(entry)

        for key in buckets:
            buckets[key].sort(key=lambda e: e["market_cap"], reverse=True)
            buckets[key] = buckets[key][:MAX_PER_SESSION]

        days[date_str] = buckets

    return {"dates": date_strs, "days": days}
