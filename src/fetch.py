"""株価データ取得."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def fetch_prices_many(
    tickers: list[str],
    years: int = 5,
    end: datetime | None = None,
) -> pd.DataFrame:
    """複数銘柄の終値を一括取得."""
    if len(tickers) < 2:
        raise ValueError("2銘柄以上を指定してください")

    end_date = end or datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    raw = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if raw.empty:
        raise RuntimeError(f"データ取得失敗: {tickers}")

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].dropna(how="all")
    else:
        prices = raw[["Close"]].dropna()
        prices.columns = [tickers[0]]

    prices = prices.dropna(how="all", axis=1)
    min_rows = int(len(prices) * 0.8)
    valid = [c for c in prices.columns if prices[c].notna().sum() >= min_rows]
    prices = prices[valid].dropna()

    if prices.shape[1] < 2:
        raise RuntimeError("有効な銘柄が2つ未満です")
    if len(prices) < 60:
        raise RuntimeError(f"データ不足 ({len(prices)} 行)")

    return prices


def fetch_prices(
    tickers: list[str],
    years: int = 5,
    end: datetime | None = None,
) -> pd.DataFrame:
    """終値を取得して DataFrame で返す."""
    if len(tickers) != 2:
        raise ValueError("2銘柄を指定してください")

    end_date = end or datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    raw = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if raw.empty:
        raise RuntimeError(f"データ取得失敗: {tickers}")

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].dropna()
    else:
        prices = raw[["Close"]].dropna()
        prices.columns = [tickers[0]]

    prices = prices.dropna()
    if len(prices) < 60:
        raise RuntimeError(f"データ不足 ({len(prices)} 行)。ティッカーを確認してください")

    return prices


def fetch_ohlc(
    ticker: str,
    years: int = 5,
    end: datetime | None = None,
) -> pd.DataFrame:
    """単一銘柄の OHLC を取得."""
    end_date = end or datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    raw = yf.download(
        ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
    )

    if raw.empty:
        raise RuntimeError(f"データ取得失敗: {ticker}")

    ohlc = raw[["Open", "High", "Low", "Close"]].dropna()
    if len(ohlc) < 60:
        raise RuntimeError(f"データ不足 ({len(ohlc)} 行): {ticker}")

    return ohlc
