"""
Simulates a trade for every signal day: enter next day's open, exit at
+2R target, -1R stop, or after max_hold_days, whichever comes first.
R is defined using ATR at signal time.
"""
import pandas as pd
from setups import add_indicators, SETUPS


def simulate_trades(df, signal, r_target=2.0, r_stop=1.0, max_hold_days=10):
    df = add_indicators(df)
    trades = []
    signal_days = df.index[signal]

    for sig_date in signal_days:
        loc = df.index.get_loc(sig_date)
        if loc + 1 >= len(df):
            continue

        entry_row = df.iloc[loc + 1]
        entry_price = entry_row["open"]
        atr = df.iloc[loc]["atr"]
        if pd.isna(atr) or atr == 0:
            continue

        stop_price = entry_price - (atr * r_stop)
        target_price = entry_price + (atr * r_target)

        exit_price = None
        exit_reason = None
        window = df.iloc[loc + 1: loc + 1 + max_hold_days]

        for _, row in window.iterrows():
            if row["low"] <= stop_price:
                exit_price, exit_reason = stop_price, "stop"
                break
            if row["high"] >= target_price:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            if len(window) == 0:
                continue
            exit_price, exit_reason = window.iloc[-1]["close"], "timeout"

        r_multiple = (exit_price - entry_price) / (entry_price - stop_price)
        trades.append({
            "signal_date": sig_date,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "r_multiple": r_multiple,
        })

    return pd.DataFrame(trades)


def compute_stats(trades_df):
    if trades_df.empty:
        return {"trades": 0, "win_rate": None, "avg_r": None, "max_drawdown": None}

    wins = trades_df["r_multiple"] > 0
    win_rate = wins.mean()
    avg_r = trades_df["r_multiple"].mean()

    cumulative = trades_df["r_multiple"].cumsum()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max)
    max_drawdown = drawdown.min()

    return {
        "trades": len(trades_df),
        "win_rate": round(win_rate * 100, 1),
        "avg_r": round(avg_r, 2),
        "max_drawdown": round(max_drawdown, 2),
    }


def backtest_setup(ticker_data, setup_name, **kwargs):
    """Runs one setup across all tickers, returns combined trades + stats."""
    setup_fn = SETUPS[setup_name]
    all_trades = []

    for ticker, df in ticker_data.items():
        signal = setup_fn(df)
        trades = simulate_trades(df, signal, **kwargs)
        if not trades.empty:
            trades["ticker"] = ticker
            all_trades.append(trades)

    combined = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    stats = compute_stats(combined)
    return combined, stats
