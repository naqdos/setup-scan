"""
Pulls daily OHLCV data for a list of tickers using yfinance.
Free, no API key required.
"""
import yfinance as yf
import pandas as pd


def get_sp500_tickers():
    """Scrapes the current S&P 500 ticker list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url)[0]
    tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
    return tickers


def download_data(tickers, period="2y", interval="1d"):
    """
    Downloads OHLCV data for a list of tickers.
    Returns a dict of {ticker: DataFrame}, skipping any that fail.
    """
    data = {}
    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 60:
                continue
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.rename(columns=str.lower)
            data[ticker] = df
        except Exception as e:
            print(f"  skipped {ticker}: {e}")
        if (i + 1) % 25 == 0:
            print(f"  downloaded {i + 1}/{len(tickers)}")
    return data


if __name__ == "__main__":
    # quick test with a small universe
    test_tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
    data = download_data(test_tickers)
    for t, df in data.items():
        print(t, df.shape, df.index.min(), df.index.max())
