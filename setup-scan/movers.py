"""
Ranks the watchlist by today's price move and volume, independent of the
momentum score (which measures weeks/months of positioning, not today).
"""
import pandas as pd
from analysis import fetch_ticker
from setups import add_indicators
from scan import DEFAULT_SCAN_LIST


def get_movers(tickers=None):
    tickers = tickers or DEFAULT_SCAN_LIST
    results = []

    for ticker in tickers:
        try:
            df = fetch_ticker(ticker, period="3mo")
            if df is None or len(df) < 21:
                results.append({"ticker": ticker, "error": "Not enough data"})
                continue

            df = add_indicators(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            pct_change = round((latest["close"] / prev["close"] - 1) * 100, 2)
            rvol = round(latest["volume"] / df["avg_vol"].iloc[-1], 2) if df["avg_vol"].iloc[-1] else None

            results.append({
                "ticker": ticker,
                "close": round(float(latest["close"]), 2),
                "pct_change_today": pct_change,
                "rvol": rvol,
                "volume": int(latest["volume"]),
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    ok = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    ok.sort(key=lambda r: abs(r["pct_change_today"]), reverse=True)
    return ok + failed
