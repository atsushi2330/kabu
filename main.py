"""2銘柄ペアのコインテグレーション分析 CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.cointegration import analyze_pair
from src.fetch import fetch_prices
from src.report import format_report
from src.visualize import plot_pair_analysis

DEFAULT_TICKERS = ["8306.T", "8316.T"]
DEFAULT_NAMES = "三菱UFJ×みずほ"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="2銘柄ペアのコインテグレーション分析（Engle-Granger + OU半減期）",
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        default=DEFAULT_TICKERS,
        help="ティッカー2つ（例: 8306.T 8316.T）",
    )
    parser.add_argument("--name", default=DEFAULT_NAMES, help="ペア表示名")
    parser.add_argument("--years", type=int, default=5, help="取得年数")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pair_analysis.png"),
        help="グラフ出力パス",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = args.tickers

    if len(tickers) != 2:
        raise SystemExit("ティッカーは2つ指定してください（例: python main.py 8306.T 8316.T）")

    print(f"データ取得中: {tickers[0]} × {tickers[1]} ({args.years}年)...")
    prices = fetch_prices(tickers, years=args.years)
    print(f"  → {len(prices)} 営業日分取得")

    result = analyze_pair(prices)
    report = format_report(result, pair_name=args.name)
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("cp932", errors="replace").decode("cp932"))

    out = plot_pair_analysis(prices, result, args.output, pair_name=args.name)
    print(f"Graph saved: {out.resolve()}")


if __name__ == "__main__":
    main()
