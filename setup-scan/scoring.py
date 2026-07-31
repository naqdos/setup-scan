"""
Momentum Score: a single 0-100 number combining four inputs.

Each input is mapped onto its own 0-100 scale first, then combined with
fixed weights. The mapping ranges and weights below are a starting point —
tune them and the score becomes an actual model you can explain, not just
a formula.

Weights (must sum to 1.0):
    RS vs SPY        30%  -- is it outperforming the market
    RVOL             20%  -- is volume showing conviction right now
    Dist. from high  30%  -- how close to its own 52-week high
    Trend            20%  -- is price above its own trend line (EMA)
"""

WEIGHTS = {
    "rs": 0.30,
    "rvol": 0.20,
    "dist_from_high": 0.30,
    "trend": 0.20,
}


def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def score_rs(rs_pct):
    """Maps RS of -30%..+30% onto 0..100."""
    if rs_pct is None:
        return 50.0
    return _clamp((rs_pct + 30) / 60 * 100)


def score_rvol(rvol):
    """Maps RVOL of 0x..3x onto 0..100. 1x (average volume) lands at ~33."""
    if rvol is None:
        return 50.0
    return _clamp((rvol / 3) * 100)


def score_dist_from_high(dist_pct):
    """Maps distance-from-52w-high of -50%..0% onto 0..100. At the high = 100."""
    if dist_pct is None:
        return 50.0
    return _clamp((dist_pct + 50) / 50 * 100)


def score_trend(close, ema):
    """Maps price's %-distance from its EMA of -10%..+10% onto 0..100."""
    if not ema:
        return 50.0
    pct = (close / ema - 1) * 100
    return _clamp((pct + 10) / 20 * 100)


def momentum_score(rs_pct, rvol, dist_from_high_pct, close, ema):
    components = {
        "rs": round(score_rs(rs_pct), 1),
        "rvol": round(score_rvol(rvol), 1),
        "dist_from_high": round(score_dist_from_high(dist_from_high_pct), 1),
        "trend": round(score_trend(close, ema), 1),
    }
    total = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 1), components
