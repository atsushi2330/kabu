"""単一銘柄・押し目買いバックテスト CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from src.fetch import fetch_ohlc
from src.single_backtest import SingleBacktestResult, run_dip_buy_backtest

NAMES = {
    "8411.T": "みずほFG",
    "8308.T": "りそなHD",
    "7201.T": "日産",
}


def format_report(result: SingleBacktestResult) -> str:
    name = NAMES.get(result.ticker, result.ticker)
    p = result.params
    tp = sum(1 for t in result.trades if t.exit_reason == "take_profit")
    sl = sum(1 for t in result.trades if t.exit_reason == "stop_loss")
    open_tr = sum(1 for t in result.trades if t.exit_reason == "end_of_data")

    lines = [
        "",
        f"=== Dip Buy Backtest: {name} ({result.ticker}) ===",
        "",
        "[Parameters]",
        f"  Entry        : prev day drop >= {p['entry_drop_pct']}% -> buy at close",
        f"  Take profit  : +{p['take_profit_pct']}% from entry",
        f"  Stop loss    : -{p['stop_loss_pct']}% from entry",
        f"  Cost         : {p['cost_bps']} bps / trade side",
        f"  Capital      : {p['initial_capital']:,.0f} JPY",
        "",
        "[Performance]",
        f"  Total return : {result.total_return_pct:+.2f} %",
        f"  Buy & Hold   : {result.buy_hold_return_pct:+.2f} %",
        f"  Sharpe ratio : {result.sharpe_ratio:.2f}",
        f"  Max drawdown : {result.max_drawdown_pct:.2f} %",
        f"  Win rate     : {result.win_rate_pct:.1f} %",
        f"  Trades       : {result.num_trades} (signals: {result.num_signals})",
        f"  Exit breakdown: TP={tp} SL={sl} open={open_tr}",
        f"  Avg holding  : {result.avg_holding_days:.1f} days",
        "",
    ]

    if result.trades:
        lines.append("[All trades]")
        for tr in result.trades:
            lines.append(
                f"  {tr.entry_date.date()} -> {tr.exit_date.date()}  "
                f"{tr.entry_price:,.0f}->{tr.exit_price:,.0f}  "
                f"{tr.pnl_pct:+.2f}%  PnL:{tr.pnl:+,.0f}  "
                f"({tr.holding_days}d, {tr.exit_reason})"
            )
        lines.append("")

    return "\n".join(lines)


def plot_result(ohlc: pd.DataFrame, result: SingleBacktestResult, output: Path) -> Path:
    name = NAMES.get(result.ticker, result.ticker)
    output.parent.mkdir(parents=True, exist_ok=True)

    close = ohlc["Close"].squeeze()
    bh = close / close.iloc[1] * result.params["initial_capital"]
    eq = result.equity_curve.reindex(bh.index, method="ffill").fillna(result.params["initial_capital"])

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [2, 1]})

    ax0 = axes[0]
    ax0.plot(bh.index, bh.values, label="Buy & Hold", color="gray", alpha=0.7, linewidth=1.5)
    ax0.plot(eq.index, eq.values, label="Dip Buy Strategy", color="steelblue", linewidth=2)
    for tr in result.trades:
        color = "green" if tr.pnl > 0 else "red"
        ax0.axvspan(tr.entry_date, tr.exit_date, alpha=0.15, color=color)
    p = result.params
    ax0.set_title(
        f"{name} — {p['entry_drop_pct']:.0f}% drop buy / "
        f"+{p['take_profit_pct']:.0f}% TP / -{p['stop_loss_pct']:.0f}% SL"
    )
    ax0.set_ylabel("Equity (JPY)")
    ax0.legend()
    ax0.grid(True, alpha=0.3)

    ax1 = axes[1]
    daily_ret = (close.pct_change() * 100).squeeze()
    ax1.bar(daily_ret.index, daily_ret.to_numpy(), color="lightgray", width=1.0, alpha=0.6)
    entries = [tr.entry_date for tr in result.trades]
    entry_rets = daily_ret.reindex(entries).dropna()
    ax1.scatter(
        entry_rets.index,
        entry_rets.values,
        color="blue",
        s=40,
        zorder=5,
        label=f"Entry (-{result.params['entry_drop_pct']:.0f}% day)",
    )
    ax1.axhline(-result.params["entry_drop_pct"], color="red", linestyle="--", linewidth=1, alpha=0.7)
    ax1.set_ylabel("Daily return (%)")
    ax1.set_xlabel("Date")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="単一銘柄 押し目買いバックテスト")
    parser.add_argument("tickers", nargs="*", default=["8411.T", "8308.T"])
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--entry-drop", type=float, default=5.0)
    parser.add_argument("--take-profit", type=float, default=3.0)
    parser.add_argument("--stop-loss", type=float, default=4.0)
    parser.add_argument("--capital", type=float, default=1_000_000)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summaries: list[dict] = []

    for ticker in args.tickers:
        print(f"Fetching {ticker} ({args.years}y)...")
        ohlc = fetch_ohlc(ticker, years=args.years)
        ohlc.attrs["ticker"] = ticker
        print(f"  -> {len(ohlc)} days")

        result = run_dip_buy_backtest(
            ohlc,
            entry_drop_pct=args.entry_drop,
            take_profit_pct=args.take_profit,
            stop_loss_pct=args.stop_loss,
            initial_capital=args.capital,
            cost_bps=args.cost_bps,
        )

        report = format_report(result)
        try:
            print(report)
        except UnicodeEncodeError:
            print(report.encode("cp932", errors="replace").decode("cp932"))

        slug = ticker.replace(".", "_")
        out = args.output_dir / f"single_dip_{slug}.png"
        plot_result(ohlc, result, out)
        print(f"Graph saved: {out.resolve()}")
        print()

        summaries.append(
            {
                "ticker": ticker,
                "name": NAMES.get(ticker, ticker),
                "return": result.total_return_pct,
                "bh": result.buy_hold_return_pct,
                "win_rate": result.win_rate_pct,
                "trades": result.num_trades,
                "max_dd": result.max_drawdown_pct,
            }
        )

    if len(summaries) > 1:
        print("=== Comparison ===")
        print(f"{'Name':12s} {'Strategy':>10s} {'B&H':>10s} {'Win%':>7s} {'Trades':>7s} {'MaxDD':>8s}")
        print("-" * 58)
        for s in summaries:
            print(
                f"{s['name']:12s} {s['return']:+9.2f}% {s['bh']:+9.2f}% "
                f"{s['win_rate']:6.1f}% {s['trades']:7d} {s['max_dd']:7.2f}%"
            )


if __name__ == "__main__":
    main()
