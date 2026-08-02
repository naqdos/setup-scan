"""
Pulls fundamental data for one ticker via yfinance's `.info` property.
Separate from analysis.py's price-history fetch since this is a different
kind of call (company metadata, not OHLCV bars) — heavier and more prone
to transient failures, so this retries once before giving up.
"""
import time
import yfinance as yf


def fetch_fundamentals(ticker, retries=1, retry_delay=1.5):
    last_error = None
    for attempt in range(retries + 1):
        try:
            info = yf.Ticker(ticker).info
            if info:
                return _parse_info(info)
            last_error = "empty response"
        except Exception as e:
            last_error = e

        if attempt < retries:
            time.sleep(retry_delay)

    return None


def _parse_info(info):
    return {
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("trailingPegRatio") or info.get("pegRatio"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
        "price_to_book": info.get("priceToBook"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "market_cap": info.get("marketCap"),
        "target_mean_price": info.get("targetMeanPrice"),
        "recommendation_key": info.get("recommendationKey"),
    }


def format_market_cap(value):
    if value is None:
        return None
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"
