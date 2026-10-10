"""コインテグレーションペアスキャナ CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.fetch import fetch_prices_many
from src.scanner import SECTOR_PRESETS, scan_pairs, to_dataframe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="コインテグレーションペアスキャナ")
    parser.add_argument(
        "--sector",
        choices=list(SECTOR_PRESETS.keys()),
        help="プリセットセクター (banks, electronics, auto)",
    )
    parser.add_argument(
        "--tickers",
        help="カンマ区切りティッカー (例: 8306.T,8316.T,8411.T)",
    )
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/scan_results.csv"),
    )
    parser.add_argument("--top", type=int, default=10, help="表示件数")
    return parser.parse_args()


def format_table(df, top: int) -> str:
    lines = [
        "",
        f"{'Rank':>4}  {'Pair':<28} {'Coint_p':>8} {'ADF_p':>8} {'HalfLife':>9} {'Z/yr':>5} {'Score':>6}  OK",
        "-" * 82,
    ]
    for i, row in df.head(top).iterrows():
        hl = row["half_life"]
        hl_str = f"{hl:8.1f}d" if hl == hl and hl < 1e6 else "     N/A"
        ok = " *" if row["valid"] else ""
        lines.append(
            f"{i+1:4d}  {row['pair']:<28} {row['coint_p']:8.4f} {row['adf_p']:8.4f} "
            f"{hl_str} {row['z_per_year']:5.1f} {row['score']:6.1f}{ok}"
        )
    valid_count = int(df["valid"].sum())
    lines.append("")
    lines.append(f"Total pairs: {len(df)}  |  Valid (p<0.05 x2): {valid_count}")
    lines.append("  * = cointegrated")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    if args.sector:
        names = SECTOR_PRESETS[args.sector]
        tickers = list(names.keys())
        label = args.sector
    elif args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]
        names = {t: t.replace(".T", "") for t in tickers}
        label = "custom"
    else:
        names = SECTOR_PRESETS["banks"]
        tickers = list(names.keys())
        label = "banks (default)"

    print(f"Scanning {label}: {len(tickers)} stocks -> {len(tickers)*(len(tickers)-1)//2} pairs")
    print(f"Fetching {args.years}y data...")
    prices = fetch_prices_many(tickers, years=args.years)
    print(f"  -> {len(prices)} days, {prices.shape[1]} stocks OK")

    rows = scan_pairs(prices, names=names)
    df = to_dataframe(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    table = format_table(df.reset_index(drop=True), args.top)
    try:
        print(table)
    except UnicodeEncodeError:
        print(table.encode("cp932", errors="replace").decode("cp932"))

    print(f"CSV saved: {args.output.resolve()}")


if __name__ == "__main__":
    main()
