# Setup Scan — Ticker Analyzer

Type a ticker, get a live snapshot: RS vs SPY, RVOL, ADR%, ATR, distance from
52-week high/low, and whether it's currently showing one of your three setups
(MA bounce, breakout, undercut-rally).

## Setup

```
pip install flask yfinance pandas numpy
```

## Run

```
python app.py
```

Then open http://localhost:5000 in your browser and type a ticker.

## Files

- `app.py` — Flask server. `/` = single-ticker page, `/scan` = daily scan page
- `analysis.py` — pulls live data via yfinance, computes stats, checks setup
  signals, computes the momentum score
- `scoring.py` — the momentum score model (RS, RVOL, distance from high, trend
  combined into one 0-100 number). Weights are documented at the top of the
  file — tune them and it's a model you can actually explain
- `scan.py` — runs the analysis across a fixed watchlist (edit
  `DEFAULT_SCAN_LIST` to change which tickers), sorted by score
- `setups.py`, `backtest.py`, `data.py`, `main.py` — the original backtester;
  `analysis.py` reuses the setup-detection functions from `setups.py`
- `static/index.html` — single-ticker page
- `static/scan.html` — daily scan table page

## How it works

1. You type a ticker and hit Scan
2. The browser calls `/api/analyze?ticker=NVDA`
3. `app.py` calls `analysis.analyze()`, which downloads ~1 year of daily data
   for that ticker (and SPY, for relative strength), computes the stats, and
   checks if the most recent day matches any of your three setups
4. The page renders the result

## Tuning

Same as the backtester — the setup thresholds in `setups.py` are a first pass.
Adjust EMA period, volume multiplier, and undercut tolerance to match your
actual rules, then re-run.

## Making it a shareable link (later)

Right now this only runs on your own machine (`localhost`). To get a real URL
you can send to your Discord — deploy `app.py` to a free host like Render or
Railway. That's a separate step once you're happy with how it works locally.
