"""バックテスト期間とベンチマーク比較."""

import pandas as pd
import yfinance as yf

from src.backtest import run_backtest
from src.fetch import fetch_prices


def period_return(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> tuple[float, float, float]:
    raw = yf.download(
        ticker,
        start=str(start.date()),
        end=str((end + pd.Timedelta(days=5)).date()),
        progress=False,
        auto_adjust=True,
    )
    if raw.empty:
        return float("nan"), float("nan"), float("nan")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    ret = (close.iloc[-1] / close.iloc[0] - 1) * 100
    norm = close / close.iloc[0]
    dd = ((norm - norm.cummax()) / norm.cummax()).min() * 100
    return ret, dd, float("nan")


def main() -> None:
    prices = fetch_prices(["8411.T", "8308.T"], years=5)
    result = run_backtest(prices)
    start = result.equity_curve.index[0]
    end = result.equity_curve.index[-1]
    years = (end - start).days / 365.25
    pair_cagr = ((1 + result.total_return_pct / 100) ** (1 / years) - 1) * 100

    print(f"Period: {start.date()} to {end.date()} ({years:.1f} years)")
    print()
    print(f"{'Asset':22s} {'Return':>10s} {'MaxDD':>10s}")
    print("-" * 44)
    print(
        f"{'Pair Z-score':22s} {result.total_return_pct:+9.2f}% "
        f"{result.max_drawdown_pct:9.2f}%  (CAGR {pair_cagr:.2f}%)"
    )

    benchmarks = [
        ("S&P500 (SPY)", "SPY"),
        ("NASDAQ (QQQ)", "QQQ"),
        ("TOPIX ETF (1306.T)", "1306.T"),
    ]
    for name, ticker in benchmarks:
        ret, dd, _ = period_return(ticker, start, end)
        cagr = ((1 + ret / 100) ** (1 / years) - 1) * 100 if ret == ret else float("nan")
        cagr_str = f"{cagr:.2f}%" if cagr == cagr else "N/A"
        print(f"{name:22s} {ret:+9.2f}% {dd:9.2f}%  (CAGR {cagr_str})")

    p = prices.loc[start:end]
    bh = ((p.iloc[-1, 0] / p.iloc[0, 0] - 1) * 100 + (p.iloc[-1, 1] / p.iloc[0, 1] - 1) * 100) / 2
    print(f"{'B&H 8411+8308':22s} {bh:+9.2f}%")


if __name__ == "__main__":
    main()
