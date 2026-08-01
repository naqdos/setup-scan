"""
Pulls upcoming earnings from Nasdaq's public calendar endpoint, one request
per day, then filters down to the watchlist. Much faster than checking each
ticker individually, and the speed no longer depends on watchlist size.
"""
import requests
from datetime import datetime, timedelta
from scan import DEFAULT_SCAN_LIST

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


def get_upcoming_earnings(tickers=None, days=7):
    watch = set(t.upper() for t in (tickers or DEFAULT_SCAN_LIST))
    today = datetime.now().date()
    results = []

    for i in range(days + 1):
        d = today + timedelta(days=i)
        rows = _fetch_day(d.isoformat())
        for row in rows:
            symbol = (row.get("symbol") or "").upper()
            if symbol in watch:
                results.append({
                    "ticker": symbol,
                    "earnings_date": d.isoformat(),
                    "days_away": i,
                    "eps_forecast": row.get("epsForecast"),
                    "time": row.get("time"),
                })

    results.sort(key=lambda r: r["days_away"])
    return results
