"""押し目買い戦略のパラメータスイープ."""

from __future__ import annotations

import argparse
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.fetch import fetch_ohlc
from src.single_backtest import run_dip_buy_backtest

NAMES = {
    "8411.T": "みずほFG",
    "8308.T": "りそなHD",
    "7201.T": "日産",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="押し目買いパラメータスイープ")
    p.add_argument("tickers", nargs="*", default=["8411.T", "8308.T", "7201.T"])
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--entry-drops", type=str, default="3,4,5,6,7")
    p.add_argument("--take-profits", type=str, default="2,3,4,5,6")
    p.add_argument("--stop-losses", type=str, default="2,3,4,5,6")
    p.add_argument("--min-trades", type=int, default=5)
    p.add_argument("--capital", type=float, default=1_000_000)
    p.add_argument("--cost-bps", type=float, default=10.0)
    p.add_argument("--output-dir", type=Path, default=Path("output"))
    return p.parse_args()


def _parse_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def run_sweep(
    tickers: list[str],
    years: int,
    entry_drops: list[float],
    take_profits: list[float],
    stop_losses: list[float],
    capital: float,
    cost_bps: float,
) -> pd.DataFrame:
    rows: list[dict] = []

    for ticker in tickers:
        print(f"Loading {ticker}...")
        ohlc = fetch_ohlc(ticker, years=years)
        ohlc.attrs["ticker"] = ticker
        close = ohlc["Close"].squeeze()
        bh_return = (float(close.iloc[-1]) / float(close.iloc[1]) - 1) * 100

        combos = list(product(entry_drops, take_profits, stop_losses))
        print(f"  Sweeping {len(combos)} combos for {NAMES.get(ticker, ticker)}...")

        for entry, tp, sl in combos:
            r = run_dip_buy_backtest(
                ohlc,
                entry_drop_pct=entry,
                take_profit_pct=tp,
                stop_loss_pct=sl,
                initial_capital=capital,
                cost_bps=cost_bps,
            )
            tp_n = sum(1 for t in r.trades if t.exit_reason == "take_profit")
            sl_n = sum(1 for t in r.trades if t.exit_reason == "stop_loss")
            rows.append(
                {
                    "ticker": ticker,
                    "name": NAMES.get(ticker, ticker),
                    "entry_drop": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "return_pct": r.total_return_pct,
                    "buy_hold_pct": bh_return,
                    "vs_bh": r.total_return_pct - bh_return,
                    "win_rate": r.win_rate_pct,
                    "trades": r.num_trades,
                    "tp_exits": tp_n,
                    "sl_exits": sl_n,
                    "max_dd": r.max_drawdown_pct,
                    "sharpe": r.sharpe_ratio,
                    "avg_hold": r.avg_holding_days,
                    "rr_ratio": tp / sl if sl > 0 else np.nan,
                }
            )

    return pd.DataFrame(rows)


def plot_heatmap(
    df: pd.DataFrame,
    ticker: str,
    take_profit: float,
    output: Path,
) -> None:
    sub = df[(df["ticker"] == ticker) & (df["take_profit"] == take_profit)]
    if sub.empty:
        return

    pivot = sub.pivot(index="entry_drop", columns="stop_loss", values="return_pct")
    name = NAMES.get(ticker, ticker)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", origin="lower")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{c:.0f}%" for c in pivot.columns])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{r:.0f}%" for r in pivot.index])
    ax.set_xlabel("Stop loss")
    ax.set_ylabel("Entry drop")
    ax.set_title(f"{name} — Return % (TP=+{take_profit:.0f}%)")

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            ax.text(j, i, f"{val:+.0f}", ha="center", va="center", fontsize=8, color="black")

    fig.colorbar(im, ax=ax, label="Return %")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def print_top(df: pd.DataFrame, min_trades: int) -> None:
    valid = df[df["trades"] >= min_trades].copy()

    print()
    print(f"=== Top 10 per ticker (min {min_trades} trades) ===")
    for ticker in df["ticker"].unique():
        name = NAMES.get(ticker, ticker)
        sub = valid[valid["ticker"] == ticker].nlargest(10, "return_pct")
        print()
        print(f"--- {name} ({ticker}) ---")
        print(f"{'Entry':>6s} {'TP':>4s} {'SL':>4s} {'Return':>8s} {'Win%':>6s} {'Trades':>7s} {'MaxDD':>7s} {'R:R':>5s}")
        print("-" * 55)
        for _, r in sub.iterrows():
            print(
                f"-{r['entry_drop']:4.0f}% +{r['take_profit']:3.0f}% -{r['stop_loss']:3.0f}% "
                f"{r['return_pct']:+7.2f}% {r['win_rate']:5.1f}% {r['trades']:7.0f} "
                f"{r['max_dd']:6.2f}% {r['rr_ratio']:5.2f}"
            )

    print()
    print("=== Best combo per ticker ===")
    print(f"{'Name':10s} {'Entry':>6s} {'TP':>4s} {'SL':>4s} {'Return':>8s} {'B&H':>8s} {'Trades':>7s}")
    print("-" * 55)
    for ticker in df["ticker"].unique():
        name = NAMES.get(ticker, ticker)
        sub = valid[valid["ticker"] == ticker]
        if sub.empty:
            continue
        best = sub.loc[sub["return_pct"].idxmax()]
        print(
            f"{name:10s} -{best['entry_drop']:4.0f}% +{best['take_profit']:3.0f}% "
            f"-{best['stop_loss']:3.0f}% {best['return_pct']:+7.2f}% "
            f"{best['buy_hold_pct']:+7.2f}% {best['trades']:7.0f}"
        )

    print()
    print("=== Reference: previous rules ===")
    refs = [
        ("8411.T", 4, 3, 3, "+1.9%"),
        ("8308.T", 4, 3, 3, "+25.8%"),
        ("7201.T", 4, 3, 3, "-6.7%"),
        ("8411.T", 5, 3, 4, "+3.5%"),
        ("8308.T", 5, 3, 4, "+9.0%"),
        ("7201.T", 5, 3, 4, "-19.7%"),
    ]
    for ticker, entry, tp, sl, _ in refs:
        row = df[
            (df["ticker"] == ticker)
            & (df["entry_drop"] == entry)
            & (df["take_profit"] == tp)
            & (df["stop_loss"] == sl)
        ]
        if not row.empty:
            r = row.iloc[0]
            print(
                f"  {NAMES.get(ticker, ticker):8s} -{entry}% +{tp}% -{sl}% "
                f"-> {r['return_pct']:+.2f}% ({r['trades']:.0f} trades)"
            )


def main() -> None:
    args = parse_args()
    entry_drops = _parse_list(args.entry_drops)
    take_profits = _parse_list(args.take_profits)
    stop_losses = _parse_list(args.stop_losses)

    total = len(entry_drops) * len(take_profits) * len(stop_losses) * len(args.tickers)
    print(f"Sweep: {len(entry_drops)} entries x {len(take_profits)} TP x {len(stop_losses)} SL")
    print(f"       x {len(args.tickers)} tickers = {total} backtests")

    df = run_sweep(
        args.tickers,
        args.years,
        entry_drops,
        take_profits,
        stop_losses,
        args.capital,
        args.cost_bps,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "sweep_results.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nCSV saved: {csv_path.resolve()}")

    for ticker in args.tickers:
        slug = ticker.replace(".", "_")
        for tp in [3.0, 4.0, 5.0]:
            if tp in take_profits:
                out = args.output_dir / f"sweep_heatmap_{slug}_tp{int(tp)}.png"
                plot_heatmap(df, ticker, tp, out)

    print_top(df, args.min_trades)


if __name__ == "__main__":
    main()
