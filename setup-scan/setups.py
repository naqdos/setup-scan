"""
Flags each day in a price DataFrame as a signal (True/False) for each setup.
These match Nathan's actual trading rules:
  - MA Bounce: price dips down and taps the 8, 21, or 50 EMA, then rejects
    (closes back above it on a green candle).
  - Breakout: price consolidates in a tight range (wedge/channel), then
    breaks the previous day's high AND the high of the whole consolidation,
    holding above it, on above-average volume.
  - Undercut & Rally: price dips below the PREVIOUS DAY's low, then
    reclaims it by the close (a failed breakdown / stop-run).
"""
import pandas as pd
import numpy as np


def add_indicators(df, ema_period=20, atr_period=14, avg_vol_period=20):
    """
    Shared indicator helper. Used both by the setup-detection functions below
    and by analysis.py's short/mid/long-term momentum scoring (which passes
    different ema_period values) — don't change this signature without
    checking analysis.py.
    """
    df = df.copy()
    df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(atr_period).mean()

    df["avg_vol"] = df["volume"].rolling(avg_vol_period).mean()
    df["n_day_high"] = df["high"].rolling(20).max().shift(1)
    df["n_day_low"] = df["low"].rolling(20).min().shift(1)
    return df


def ma_bounce_signal(df, tolerance=0.01):
    """
    Price dips down and taps the 8, 21, or 50 EMA, then rejects — closes
    back above that same EMA on a green candle. Fires if ANY of the three
    EMAs gets tapped-and-rejected that day. Requires the stock to still be
    generally trending up (above its own 50 EMA) so this isn't just noise
    inside a downtrend.
    """
    df = df.copy()
    ema8 = df["close"].ewm(span=8, adjust=False).mean()
    ema21 = df["close"].ewm(span=21, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()

    green_candle = df["close"] > df["open"]
    uptrend_context = df["close"] > ema50

    signal = pd.Series(False, index=df.index)
    for ema in (ema8, ema21, ema50):
        touched = df["low"] <= ema * (1 + tolerance)
        rejected = df["close"] > ema
        signal = signal | (touched & rejected)

    signal = signal & green_candle & uptrend_context
    return signal.fillna(False)


def breakout_signal(df, consolidation_days=10, max_range_pct=0.08, min_volume_mult=1.5):
    """
    Price has been consolidating in a tight range (a rough proxy for a
    wedge/channel/flag) over the prior `consolidation_days`, then closes
    above BOTH the previous day's high (PDH) and the high of that whole
    consolidation range — i.e. it clears the base and holds above it, not
    just a one-day wiggle above yesterday's high. Confirmed by volume at
    least `min_volume_mult`x the 20-day average.
    """
    df = add_indicators(df)

    base_high = df["high"].rolling(consolidation_days).max().shift(1)
    base_low = df["low"].rolling(consolidation_days).min().shift(1)
    range_pct = (base_high - base_low) / df["close"].shift(1)
    tight_consolidation = range_pct < max_range_pct

    prev_day_high = df["high"].shift(1)
    breaks_pdh = df["close"] > prev_day_high
    breaks_base_high = df["close"] > base_high
    volume_confirm = df["volume"] > (df["avg_vol"] * min_volume_mult)

    signal = tight_consolidation & breaks_pdh & breaks_base_high & volume_confirm
    return signal.fillna(False)


def undercut_rally_signal(df, tolerance=0.0):
    """
    Today's low dips below the PREVIOUS DAY's low (a stop-run / shakeout),
    but the candle closes back above that previous day's low by the close
    — a failed breakdown.
    """
    df = df.copy()
    prev_day_low = df["low"].shift(1)
    undercut = df["low"] < (prev_day_low * (1 - tolerance))
    rallied_back = df["close"] > prev_day_low
    signal = undercut & rallied_back
    return signal.fillna(False)


SETUPS = {
    "ma_bounce": ma_bounce_signal,
    "breakout": breakout_signal,
    "undercut_rally": undercut_rally_signal,
}
