"""
Checks each ticker's next earnings date and returns the ones falling
within the next `days` days.
"""
import yfinance as yf
from datetime import datetime, timedelta
from scan import DEFAULT_SCAN_LIST


def get_upcoming_earnings(tickers=None, days=7):
    tickers = tickers or DEFAULT_SCAN_LIST
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    results = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            dates_df = t.get_earnings_dates(limit=8)
            if dates_df is None or dates_df.empty:
                continue

            upcoming = [
                idx.date() for idx in dates_df.index
                if today <= idx.date() <= cutoff
            ]
            if upcoming:
                next_date = min(upcoming)
                results.append({
                    "ticker": ticker,
                    "earnings_date": str(next_date),
                    "days_away": (next_date - today).days,
                })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    ok = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    ok.sort(key=lambda r: r["days_away"])
    return ok + failed
