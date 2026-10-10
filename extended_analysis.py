"""横這い期間分析 + 合成ポートフォリオ試算."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf

from src.backtest import run_backtest
from src.fetch import fetch_prices, fetch_prices_many


@dataclass
class PeriodResult:
    label: str
    start: str
    end: str
    pair_return: float
    spy_return: float
    pair_sharpe: float
    pair_max_dd: float


def _fetch_close(ticker: str, start: str, end: str) -> pd.Series:
    raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def _period_return(series: pd.Series) -> float:
    return float((series.iloc[-1] / series.iloc[0] - 1) * 100)


def analyze_periods(ticker_a: str, ticker_b: str) -> list[PeriodResult]:
    """相場環境別にサブ期間バックテスト."""
    periods = [
        ("2022 H2 (調整)", "2022-07-01", "2022-12-31"),
        ("2023 横這い", "2023-01-01", "2023-12-31"),
        ("2024 上昇", "2024-01-01", "2024-12-31"),
        ("2025 YTD", "2025-01-01", "2025-12-31"),
    ]
    results: list[PeriodResult] = []

    for label, start, end in periods:
        try:
            prices = fetch_prices([ticker_a, ticker_b], years=10)
            prices = prices.loc[start:end]
            if len(prices) < 120:
                continue
            bt = run_backtest(prices, lookback=min(120, len(prices) // 3))
            spy = _fetch_close("SPY", start, end)
            if len(spy) < 2:
                continue
            results.append(
                PeriodResult(
                    label=label,
                    start=start,
                    end=end,
                    pair_return=bt.total_return_pct,
                    spy_return=_period_return(spy),
                    pair_sharpe=bt.sharpe_ratio,
                    pair_max_dd=bt.max_drawdown_pct,
                )
            )
        except Exception:
            continue
    return results


def composite_portfolio(
    ticker_a: str,
    ticker_b: str,
    pair_weight: float = 0.2,
    years: int = 5,
) -> dict:
    """SPY + ペア戦略の合成ポートフォリオ."""
    prices = fetch_prices([ticker_a, ticker_b], years=years)
    pair_bt = run_backtest(prices)
    start = pair_bt.equity_curve.index[0]
    end = pair_bt.equity_curve.index[-1]

    spy = _fetch_close("SPY", str(start.date()), str((end + pd.Timedelta(days=5)).date()))
    spy = spy.reindex(pair_bt.equity_curve.index, method="ffill").dropna()
    common = pair_bt.equity_curve.index.intersection(spy.index)
    if len(common) < 10:
        raise RuntimeError("共通期間が短すぎます")

    pair_norm = pair_bt.equity_curve.loc[common] / pair_bt.params["initial_capital"]
    spy_norm = spy.loc[common] / spy.iloc[0]

    spy_w = 1.0 - pair_weight
    composite = spy_w * spy_norm + pair_weight * pair_norm
    comp_rets = composite.pct_change().dropna()

    spy_rets = spy_norm.pct_change().dropna()
    pair_rets = pair_norm.pct_change().dropna()

    n_years = (common[-1] - common[0]).days / 365.25

    def stats(rets: pd.Series, total_mult: float) -> dict:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
        cum = (1 + rets).cumprod()
        dd = float(((cum - cum.cummax()) / cum.cummax()).min() * 100)
        cagr = ((total_mult) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0.0
        return {
            "total_return_pct": (total_mult - 1) * 100,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "max_dd_pct": dd,
        }

    return {
        "period": f"{common[0].date()} - {common[-1].date()}",
        "pair_weight": pair_weight,
        "spy_weight": spy_w,
        "pair": stats(pair_rets, float(pair_norm.iloc[-1])),
        "spy": stats(spy_rets, float(spy_norm.iloc[-1])),
        "composite": stats(comp_rets, float(composite.iloc[-1])),
        "pair_only_total": pair_bt.total_return_pct,
    }


def print_report(
    pair_name: str,
    periods: list[PeriodResult],
    composite: dict,
    kyocera_result: dict | None = None,
) -> str:
    lines = [
        "",
        "=" * 60,
        f" Extended Analysis: {pair_name}",
        "=" * 60,
        "",
        "[1] Period Breakdown (pair strategy vs SPY)",
        f"  {'Period':<18} {'Pair':>8} {'SPY':>8} {'Sharpe':>7} {'MaxDD':>8}",
        "  " + "-" * 52,
    ]
    for p in periods:
        lines.append(
            f"  {p.label:<18} {p.pair_return:+7.1f}% {p.spy_return:+7.1f}% "
            f"{p.pair_sharpe:7.2f} {p.pair_max_dd:7.1f}%"
        )

    lines += [
        "",
        f"[2] Composite Portfolio ({composite['spy_weight']*100:.0f}% SPY + "
        f"{composite['pair_weight']*100:.0f}% Pair)",
        f"  Period: {composite['period']}",
        "",
        f"  {'':12} {'Return':>8} {'CAGR':>7} {'Sharpe':>7} {'MaxDD':>8}",
        "  " + "-" * 44,
    ]
    for key, label in [("spy", "SPY only"), ("pair", "Pair only"), ("composite", "Composite")]:
        s = composite[key]
        lines.append(
            f"  {label:<12} {s['total_return_pct']:+7.1f}% {s['cagr_pct']:6.1f}% "
            f"{s['sharpe']:7.2f} {s['max_dd_pct']:7.1f}%"
        )

    if kyocera_result:
        lines += [
            "",
            "[3] Kyocera x Murata (6971 x 6981) - scan #1",
            f"  Coint p     : {kyocera_result['coint_p']:.4f}",
            f"  Backtest    : {kyocera_result['bt_return']:+.1f}%  "
            f"Sharpe {kyocera_result['bt_sharpe']:.2f}  "
            f"MaxDD {kyocera_result['bt_dd']:.1f}%",
            f"  vs 8411x8308: {kyocera_result['compare']}",
        ]

    lines += [
        "",
        "[4] Takeaways",
        "  - Pair trading wins when SPY is flat/negative (check period table)",
        "  - Composite: slightly lower return than SPY alone in bull market,",
        "    but diversification may help in drawdowns",
        "  - Best cointegrated pair != best backtest pair always",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    from src.cointegration import analyze_pair

    # Kyocera x Murata
    k_prices = fetch_prices(["6971.T", "6981.T"], years=5)
    k_analysis = analyze_pair(k_prices)
    k_bt = run_backtest(k_prices)

    # 8411 x 8308 comparison
    b_prices = fetch_prices(["8411.T", "8308.T"], years=5)
    b_bt = run_backtest(b_prices)

    if k_bt.total_return_pct > b_bt.total_return_pct:
        compare = f"Kyocera pair better (+{k_bt.total_return_pct - b_bt.total_return_pct:.1f}% vs bank pair)"
    else:
        compare = f"Bank pair still better (+{b_bt.total_return_pct - k_bt.total_return_pct:.1f}% vs Kyocera)"

    kyocera_info = {
        "coint_p": k_analysis.coint_pvalue,
        "bt_return": k_bt.total_return_pct,
        "bt_sharpe": k_bt.sharpe_ratio,
        "bt_dd": k_bt.max_drawdown_pct,
        "compare": compare,
    }

    # Period analysis on best bank pair
    periods = analyze_periods("8411.T", "8308.T")

    # Composite: 80% SPY + 20% bank pair
    composite = composite_portfolio("8411.T", "8308.T", pair_weight=0.2)

    report = print_report("8411x8308 + benchmarks", periods, composite, kyocera_info)
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("cp932", errors="replace").decode("cp932"))

    out = __import__("pathlib").Path("output/extended_analysis.txt")
    out.write_text(report, encoding="utf-8")
    print(f"Report saved: {out.resolve()}")


if __name__ == "__main__":
    main()
