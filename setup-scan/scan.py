"""
Runs analyze() across a list of tickers (no per-ticker backtest, for speed)
and returns them sorted by momentum score, highest first.
"""
from analysis import analyze

DEFAULT_SCAN_LIST = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN",
    "AVGO", "NFLX", "CRM", "ADBE", "COST", "PANW", "SHOP", "PLTR",
    "CRWD", "UBER", "LLY", "V",
]


def run_scan(tickers=None):
    tickers = tickers or DEFAULT_SCAN_LIST
    results = []
    for ticker in tickers:
        try:
            r = analyze(ticker, include_backtest=False)
            if "error" in r:
                r["ticker"] = ticker
            results.append(r)
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    ok = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    ok.sort(key=lambda r: r["momentum_score"], reverse=True)
    return ok + failed
