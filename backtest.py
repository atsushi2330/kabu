"""Zスコア平均回帰戦略バックテスト CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.backtest import run_backtest
from src.backtest_report import format_backtest_report
from src.backtest_visualize import plot_backtest
from src.fetch import fetch_prices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2銘柄ペア Zスコア戦略バックテスト")
    parser.add_argument("tickers", nargs="*", default=["8411.T", "8308.T"])
    parser.add_argument("--name", default="みずほFG x りそな")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--lookback", type=int, default=252, help="beta推定窓（日）")
    parser.add_argument("--z-window", type=int, default=60, help="Zスコア計算窓（日）")
    parser.add_argument("--entry-z", type=float, default=2.0)
    parser.add_argument("--exit-z", type=float, default=1.0, help="|Z|がこの値未満で決済 (exit-leg-pct未指定時)")
    parser.add_argument("--stop-z", type=float, default=4.0)
    parser.add_argument(
        "--individual-legs",
        action="store_true",
        default=True,
        help="各レッグ個別決済 (default: on)",
    )
    parser.add_argument("--no-individual-legs", action="store_false", dest="individual_legs")
    parser.add_argument("--take-profit", type=float, default=4.0, help="利確: お得方向にこの%")
    parser.add_argument("--stop-loss", type=float, default=3.0, help="損切: 不利方向にこの%")
    parser.add_argument(
        "--exit-leg-pct",
        type=float,
        default=None,
        help="(旧) 両レッグ同時決済モード用",
    )
    parser.add_argument("--stop-leg-pct", type=float, default=None)
    parser.add_argument("--exit-mode", choices=["and", "or"], default="and")
    parser.add_argument("--max-holding", type=int, default=90, help="最大保有日数 (両レッグ強制決済)")
    parser.add_argument("--capital", type=float, default=1_000_000)
    parser.add_argument("--cost-bps", type=float, default=10.0, help="1レッグあたり手数料(bps)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/backtest_8411_8308_trades.png"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.tickers) != 2:
        raise SystemExit("ティッカーは2つ指定してください")

    print(f"Fetching {args.tickers[0]} x {args.tickers[1]} ({args.years}y)...")
    prices = fetch_prices(args.tickers, years=args.years)
    print(f"  -> {len(prices)} days")

    print("Running backtest...")
    result = run_backtest(
        prices,
        lookback=args.lookback,
        z_window=args.z_window,
        entry_z=args.entry_z,
        exit_z=args.exit_z,
        stop_z=args.stop_z,
        exit_leg_pct=args.exit_leg_pct,
        stop_leg_pct=args.stop_leg_pct,
        exit_mode=args.exit_mode,
        individual_leg_exit=args.individual_legs and args.exit_leg_pct is None,
        take_profit_leg_pct=args.take_profit,
        stop_loss_leg_pct=args.stop_loss,
        max_holding_days=args.max_holding,
        initial_capital=args.capital,
        cost_bps=args.cost_bps,
    )

    report = format_backtest_report(result, pair_name=args.name)
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("cp932", errors="replace").decode("cp932"))

    out = plot_backtest(prices, result, args.output, pair_name=args.name)
    print(f"Graph saved: {out.resolve()}")


if __name__ == "__main__":
    main()
