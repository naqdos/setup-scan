"""
Computes a current snapshot for one ticker: RS vs SPY, RVOL, ADR%, ATR,
distance from HOD/LOD, and whether today matches one of the three setups.
"""
import yfinance as yf
import pandas as pd
from setups import add_indicators, ma_bounce_signal, breakout_signal, undercut_rally_signal, SETUPS
from backtest import simulate_trades, compute_stats
from scoring import momentum_score, fundamental_score
from fundamentals import fetch_fundamentals, format_market_cap


def fetch_ticker(ticker, period="2y"):
    df = yf.download(ticker, period=period, interval="1d", progress=False)
    if df.empty:
        return None
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns=str.lower)
    return df


def relative_strength(ticker_df, spy_df, lookback=63):
    """Simple RS: ticker's % return vs SPY's % return over `lookback` days."""
    if len(ticker_df) <= lookback or len(spy_df) <= lookback:
        return None
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

    # Short-term (~2 weeks) and long-term (~1 year) views, alongside the
    # overall score above (which is ~3-month RS + 52-week high + 20-EMA trend)
    df_short = add_indicators(df, ema_period=10)
    df_long = add_indicators(df, ema_period=50)

    rs_short = relative_strength(df, spy, lookback=10) if spy is not None else None
    rs_long = relative_strength(df, spy, lookback=252) if spy is not None else None

    high_20d = df["high"].rolling(20).max().shift(1).iloc[-1]
    dist_20d_high = round((latest["close"] / high_20d - 1) * 100, 2) if pd.notna(high_20d) else None

    ema10 = float(df_short["ema"].iloc[-1]) if pd.notna(df_short["ema"].iloc[-1]) else None
    ema50 = float(df_long["ema"].iloc[-1]) if pd.notna(df_long["ema"].iloc[-1]) else None

    short_score, short_components = momentum_score(
        rs_pct=rs_short, rvol=rvol, dist_from_high_pct=dist_20d_high,
        close=float(latest["close"]), ema=ema10,
    )
    long_technical_score, long_components = momentum_score(
        rs_pct=rs_long, rvol=rvol, dist_from_high_pct=dist_from_hod,
        close=float(latest["close"]), ema=ema50,
    )

    # Fundamentals — separate rating, and blended heavily into long-term
    # (70% fundamentals / 30% long-term technical), since a year-long price
    # trend alone doesn't capture valuation, growth, or profitability.
    fund_data = None
    fund_total = None
    fund_components = None
    try:
        fund_data = fetch_fundamentals(ticker)
    except Exception:
        fund_data = None

    if fund_data:
        fund_total, fund_components = fundamental_score(
            peg_ratio=fund_data["peg_ratio"],
            revenue_growth=fund_data["revenue_growth"],
            earnings_growth=fund_data["earnings_growth"],
            profit_margin=fund_data["profit_margin"],
            operating_margin=fund_data["operating_margin"],
            recommendation_key=fund_data["recommendation_key"],
            target_mean_price=fund_data["target_mean_price"],
            current_price=float(latest["close"]),
        )

    if fund_total is not None:
        long_score = round(0.7 * fund_total + 0.3 * long_technical_score, 1)
    else:
        long_score = long_technical_score

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
        "short_term_score": short_score,
        "short_term_components": short_components,
        "long_term_score": long_score,
        "long_term_technical_score": long_technical_score,
        "long_term_components": long_components,
        "fundamental_score": fund_total,
        "fundamental_components": fund_components,
        "fundamentals": {
            **(fund_data or {}),
            "market_cap_formatted": format_market_cap(fund_data["market_cap"]) if fund_data else None,
        } if fund_data else None,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(analyze("AAPL"), indent=2))
