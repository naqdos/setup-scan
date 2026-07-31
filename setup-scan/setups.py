"""
Flags each day in a price DataFrame as a signal (True/False) for each setup.
Adjust the parameters (windows, thresholds) to match how you actually trade.
"""
import pandas as pd
import numpy as np


def add_indicators(df, ema_period=20, atr_period=14, avg_vol_period=20):
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


def ma_bounce_signal(df, ema_period=20, tolerance=0.015):
    """
    Uptrend (price above EMA over last 10 days), pulls back to within
    `tolerance` of the EMA, then closes green and back above it.
    """
    df = add_indicators(df, ema_period=ema_period)
    uptrend = df["close"].shift(1).rolling(10).mean() > df["ema"].shift(1).rolling(10).mean()
    touched_ema = (df["low"].shift(1) <= df["ema"].shift(1) * (1 + tolerance))
    closed_above = df["close"] > df["ema"]
    green_candle = df["close"] > df["open"]
    signal = uptrend & touched_ema & closed_above & green_candle
    return signal.fillna(False)


def breakout_signal(df, min_volume_mult=1.5):
    """
    Closes above the prior 20-day high on volume above `min_volume_mult`x
    the 20-day average volume.
    """
    df = add_indicators(df)
    breaks_high = df["close"] > df["n_day_high"]
    volume_confirm = df["volume"] > (df["avg_vol"] * min_volume_mult)
    signal = breaks_high & volume_confirm
    return signal.fillna(False)


def undercut_rally_signal(df, undercut_tolerance=0.01):
    """
    Intraday low dips below the prior 20-day low (a shakeout), but the
    candle closes back above that prior low by end of day.
    """
    df = add_indicators(df)
    undercut = df["low"] < (df["n_day_low"] * (1 - undercut_tolerance))
    rallied_back = df["close"] > df["n_day_low"]
    signal = undercut & rallied_back
    return signal.fillna(False)


SETUPS = {
    "ma_bounce": ma_bounce_signal,
    "breakout": breakout_signal,
    "undercut_rally": undercut_rally_signal,
}
