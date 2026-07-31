"""
Computes a current snapshot for one ticker: RS vs SPY, RVOL, ADR%, ATR,
distance from HOD/LOD, and whether today matches one of the three setups.
"""
import yfinance as yf
import pandas as pd
from setups import add_indicators, ma_bounce_signal, breakout_signal, undercut_rally_signal, SETUPS
from backtest import simulate_trades, compute_stats
from scoring import momentum_score


def fetch_ticker(ticker, period="2y"):
    df = yf.download(ticker, period=period, interval="1d", progress=False)
    if df.empty:
        return None
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns=str.lower)
    return df


def relative_strength(ticker_df, spy_df, lookback=63):
    """Simple RS: ticker's % return vs SPY's % return over `lookback` days."""
    t_ret = ticker_df["close"].iloc[-1] / ticker_df["close"].iloc[-lookback] - 1
    s_ret = spy_df["close"].iloc[-1] / spy_df["close"].iloc[-lookback] - 1
    return round((t_ret - s_ret) * 100, 2)


def historical_setup_stats(df):
    """
    Runs each setup's own historical trades on this single ticker and
    returns win rate / avg R / trade count / max drawdown for each.
    """
    signal_fns = {
        "ma_bounce": ma_bounce_signal,
        "breakout": breakout_signal,
        "undercut_rally": undercut_rally_signal,
    }
    stats = {}
    for name, fn in signal_fns.items():
        signal = fn(df)
        trades = simulate_trades(df, signal)
        stats[name] = compute_stats(trades)
    return stats


def analyze(ticker, include_backtest=True):
    df = fetch_ticker(ticker)
    if df is None or len(df) < 70:
        return {"error": f"Not enough data for {ticker}"}

    spy = fetch_ticker("SPY")
    df = add_indicators(df)

    latest = df.iloc[-1]
    adr_pct = round(((df["high"] / df["low"] - 1).rolling(20).mean().iloc[-1]) * 100, 2)
    rvol = round(latest["volume"] / df["avg_vol"].iloc[-1], 2) if df["avg_vol"].iloc[-1] else None
    dist_from_hod = round((latest["close"] / df["high"].rolling(252).max().iloc[-1] - 1) * 100, 2)
    dist_from_lod = round((latest["close"] / df["low"].rolling(252).min().iloc[-1] - 1) * 100, 2)
    rs = relative_strength(df, spy) if spy is not None else None

    signals = {
        "ma_bounce": bool(ma_bounce_signal(df).iloc[-1]),
        "breakout": bool(breakout_signal(df).iloc[-1]),
        "undercut_rally": bool(undercut_rally_signal(df).iloc[-1]),
    }

    setup_stats = historical_setup_stats(df) if include_backtest else None

    score_total, score_components = momentum_score(
        rs_pct=rs,
        rvol=rvol,
        dist_from_high_pct=dist_from_hod,
        close=float(latest["close"]),
        ema=float(latest["ema"]) if pd.notna(latest["ema"]) else None,
    )

    return {
        "ticker": ticker.upper(),
        "close": round(float(latest["close"]), 2),
        "date": str(df.index[-1].date()),
        "rs_vs_spy": rs,
        "rvol": rvol,
        "adr_pct": adr_pct,
        "atr": round(float(latest["atr"]), 2) if pd.notna(latest["atr"]) else None,
        "dist_from_52w_high_pct": dist_from_hod,
        "dist_from_52w_low_pct": dist_from_lod,
        "signals": signals,
        "setup_stats": setup_stats,
        "momentum_score": score_total,
        "momentum_components": score_components,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(analyze("AAPL"), indent=2))
