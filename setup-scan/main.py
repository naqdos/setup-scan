"""
Runs all three setups across a ticker universe and prints/saves a report.

Usage:
    python main.py                      # uses a default ticker list
    python main.py --tickers AAPL,MSFT  # custom list
    python main.py --sp500              # pulls full current S&P 500 list
"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt

from data import download_data, get_sp500_tickers
from backtest import backtest_setup

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN",
    "AVGO", "NFLX", "CRM", "ADBE", "COST", "PANW", "SHOP", "PLTR",
]


def run(tickers, period="2y"):
    print(f"Downloading data for {len(tickers)} tickers...")
    ticker_data = download_data(tickers, period=period)
    print(f"Got data for {len(ticker_data)} tickers.\n")

    results = {}
    for setup_name in ["ma_bounce", "breakout", "undercut_rally"]:
        print(f"Backtesting: {setup_name}")
        trades, stats = backtest_setup(ticker_data, setup_name)
        results[setup_name] = (trades, stats)
        print(f"  trades={stats['trades']}  win_rate={stats['win_rate']}%  "
              f"avg_r={stats['avg_r']}  max_dd={stats['max_drawdown']}\n")

    return results


def save_report(results, outdir="."):
    summary_rows = []
    for setup_name, (trades, stats) in results.items():
        summary_rows.append({"setup": setup_name, **stats})
        if not trades.empty:
            trades.to_csv(f"{outdir}/trades_{setup_name}.csv", index=False)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(f"{outdir}/summary.csv", index=False)
    print(summary.to_string(index=False))

    # equity curve chart per setup
    fig, ax = plt.subplots(figsize=(9, 5))
    for setup_name, (trades, stats) in results.items():
        if trades.empty:
            continue
        curve = trades.sort_values("signal_date")["r_multiple"].cumsum()
        ax.plot(curve.values, label=setup_name)
    ax.set_xlabel("Trade number")
    ax.set_ylabel("Cumulative R")
    ax.set_title("Equity curve by setup (cumulative R-multiple)")
    ax.legend()
    ax.axhline(0, color="gray", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(f"{outdir}/equity_curve.png", dpi=150)
    print(f"\nSaved: {outdir}/summary.csv, per-setup trade CSVs, {outdir}/equity_curve.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", type=str, default=None,
                         help="comma-separated tickers, e.g. AAPL,MSFT")
    parser.add_argument("--sp500", action="store_true",
                         help="use the full current S&P 500 list (slow)")
    parser.add_argument("--period", type=str, default="2y")
    args = parser.parse_args()

    if args.sp500:
        tickers = get_sp500_tickers()
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = DEFAULT_TICKERS

    results = run(tickers, period=args.period)
    save_report(results)
