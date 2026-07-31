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


"""
Fundamental Score: a separate 0-100 number from company financials, not
price/volume. Same pattern as above — each input mapped to 0-100, then
combined with fixed weights.

Weights (must sum to 1.0):
    Valuation (PEG ratio)         25%  -- growth-adjusted, cheap vs expensive
    Growth (revenue + earnings)   30%  -- YoY growth rate
    Profitability (margins)       25%  -- profit + operating margin
    Analyst view                  20%  -- consensus rating + price target upside
"""

FUNDAMENTAL_WEIGHTS = {
    "valuation": 0.25,
    "growth": 0.30,
    "profitability": 0.25,
    "analyst": 0.20,
}

_RECOMMENDATION_SCORES = {
    "strong_buy": 100, "strongbuy": 100,
    "buy": 80,
    "hold": 50, "none": 50,
    "underperform": 30,
    "sell": 20,
    "strong_sell": 0, "strongsell": 0,
}


def score_peg(peg):
    """PEG of 1.0 (fair value for the growth rate) scores 100; scales down
    as PEG rises above 1, or is neutral if missing/non-positive."""
    if peg is None or peg <= 0:
        return 50.0
    return _clamp(100 - (peg - 1) * 40)


def score_growth(revenue_growth, earnings_growth):
    """Averages revenue + earnings YoY growth (as decimals, e.g. 0.15),
    maps -20%..+40% onto 0..100."""
    vals = [v for v in (revenue_growth, earnings_growth) if v is not None]
    if not vals:
        return 50.0
    avg_pct = (sum(vals) / len(vals)) * 100
    return _clamp((avg_pct + 20) / 60 * 100)


def score_profitability(profit_margin, operating_margin):
    """Averages profit + operating margin, maps -10%..+30% onto 0..100."""
    vals = [v for v in (profit_margin, operating_margin) if v is not None]
    if not vals:
        return 50.0
    avg_pct = (sum(vals) / len(vals)) * 100
    return _clamp((avg_pct + 10) / 40 * 100)


def score_analyst(recommendation_key, target_mean_price, current_price):
    """Blends analyst consensus rating with price-target upside/downside."""
    rec_score = _RECOMMENDATION_SCORES.get((recommendation_key or "").lower(), 50.0)
    upside_score = 50.0
    if target_mean_price and current_price:
        upside_pct = (target_mean_price / current_price - 1) * 100
        upside_score = _clamp((upside_pct + 20) / 40 * 100)
    return (rec_score + upside_score) / 2


def fundamental_score(peg_ratio, revenue_growth, earnings_growth, profit_margin,
                       operating_margin, recommendation_key, target_mean_price, current_price):
    components = {
        "valuation": round(score_peg(peg_ratio), 1),
        "growth": round(score_growth(revenue_growth, earnings_growth), 1),
        "profitability": round(score_profitability(profit_margin, operating_margin), 1),
        "analyst": round(score_analyst(recommendation_key, target_mean_price, current_price), 1),
    }
    total = sum(components[k] * FUNDAMENTAL_WEIGHTS[k] for k in FUNDAMENTAL_WEIGHTS)
    return round(total, 1), components
