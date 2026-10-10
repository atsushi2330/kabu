"""日産: 資産推移の描画."""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from src.fetch import fetch_ohlc
from src.single_backtest import SingleBacktestResult, run_dip_buy_backtest

TICKER = "7201.T"
CAPITAL = 1_000_000

STRATEGIES = [
    ("-1% / +10% / -1% (1000通りベスト)", 1, 10, 1, "#2563eb"),
    ("-2% / +10% / -6% (3銘柄共通)", 2, 10, 6, "#16a34a"),
    ("-4% / +3% / -3% (初期ルール)", 4, 3, 3, "#ea580c"),
]


def _fmt_yen(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    return f"{v/10_000:.0f}万"


def plot_nissan_equity(output: Path) -> Path:
    ohlc = fetch_ohlc(TICKER, years=5)
    ohlc.attrs["ticker"] = TICKER
    close = ohlc["Close"].squeeze()
    start_idx = 1

    bh = close / close.iloc[start_idx] * CAPITAL

    fig, axes = plt.subplots(3, 1, figsize=(14, 11), gridspec_kw={"height_ratios": [3, 2, 1.2]})

    ax_eq = axes[0]
    ax_eq.plot(bh.index, bh.values, label=f"B&H ({bh.iloc[-1]/CAPITAL*100-100:+.1f}%)", color="gray", linewidth=2, alpha=0.8)

    best_result: SingleBacktestResult | None = None
    for label, entry, tp, sl, color in STRATEGIES:
        result = run_dip_buy_backtest(
            ohlc,
            entry_drop_pct=entry,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            initial_capital=CAPITAL,
        )
        eq = result.equity_curve.reindex(bh.index, method="ffill").fillna(CAPITAL)
        ax_eq.plot(
            eq.index,
            eq.values,
            label=f"{label} ({result.total_return_pct:+.1f}%)",
            color=color,
            linewidth=2,
        )
        if entry == 1 and tp == 10 and sl == 1:
            best_result = result

    ax_eq.axhline(CAPITAL, color="black", linestyle=":", linewidth=1, alpha=0.4)
    ax_eq.set_ylabel("資産 (円)")
    ax_eq.set_title("日産 (7201.T) — 資産の増え方 + 株価（初期100万円）")
    ax_eq.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1_000_000:.1f}M" if x >= 1e6 else f"{x/10_000:.0f}万"))

    ax_px = ax_eq.twinx()
    ax_px.plot(close.index, close.values, color="#7c3aed", linewidth=1.5, alpha=0.55, label="株価")
    ax_px.set_ylabel("株価 (円)", color="#7c3aed")
    ax_px.tick_params(axis="y", labelcolor="#7c3aed")
    ax_px.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}"))

    h1, l1 = ax_eq.get_legend_handles_labels()
    h2, l2 = ax_px.get_legend_handles_labels()
    ax_eq.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    ax_eq.grid(True, alpha=0.3)

    # ベスト戦略のトレードタイミング + 資産
    ax_tr = axes[1]
    if best_result is not None:
        eq = best_result.equity_curve.reindex(bh.index, method="ffill").fillna(CAPITAL)
        ax_tr.fill_between(eq.index, CAPITAL, eq.values, where=eq.values >= CAPITAL, alpha=0.2, color="green", label="含み益エリア")
        ax_tr.fill_between(eq.index, CAPITAL, eq.values, where=eq.values < CAPITAL, alpha=0.2, color="red", label="含み損エリア")
        ax_tr.plot(eq.index, eq.values, color="#2563eb", linewidth=2, label="資産推移")

        for tr in best_result.trades:
            c = "green" if tr.pnl > 0 else "red"
            ax_tr.scatter(tr.entry_date, eq.reindex([tr.entry_date], method="ffill").iloc[0], marker="^", s=50, color=c, zorder=5)
            ax_tr.scatter(tr.exit_date, eq.reindex([tr.exit_date], method="ffill").iloc[0], marker="v", s=50, color=c, zorder=5)

        # マーカー凡例（トレード点はループ描画のため明示ラベルを追加）
        ax_tr.scatter([], [], marker="^", s=60, color="green", label="▲ 買い（勝ちトレード）")
        ax_tr.scatter([], [], marker="v", s=60, color="green", label="▼ 売り（勝ちトレード）")
        ax_tr.scatter([], [], marker="^", s=60, color="red", label="▲ 買い（負けトレード）")
        ax_tr.scatter([], [], marker="v", s=60, color="red", label="▼ 売り（負けトレード）")

        tp_n = sum(1 for t in best_result.trades if t.exit_reason == "take_profit")
        sl_n = sum(1 for t in best_result.trades if t.exit_reason == "stop_loss")
        ax_tr.set_title(
            f"ベストルール詳細: -1%/+10%/-1%  "
            f"({best_result.num_trades} trades, 勝率{best_result.win_rate_pct:.1f}%, "
            f"TP={tp_n} SL={sl_n})"
        )
    ax_tr.axhline(CAPITAL, color="black", linestyle=":", linewidth=1, alpha=0.4)
    ax_tr.set_ylabel("資産 (円)")
    ax_tr.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1_000_000:.1f}M" if x >= 1e6 else f"{x/10_000:.0f}万"))

    ax_tr_px = ax_tr.twinx()
    ax_tr_px.plot(close.index, close.values, color="#7c3aed", linewidth=1.2, alpha=0.45, label="株価")
    ax_tr_px.set_ylabel("株価 (円)", color="#7c3aed")
    ax_tr_px.tick_params(axis="y", labelcolor="#7c3aed")
    ax_tr_px.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}"))

    h1, l1 = ax_tr.get_legend_handles_labels()
    h2, l2 = ax_tr_px.get_legend_handles_labels()
    ax_tr.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, ncol=2)
    ax_tr.grid(True, alpha=0.3)

    # ドローダウン（ベスト戦略）
    ax_dd = axes[2]
    if best_result is not None:
        eq = best_result.equity_curve.reindex(bh.index, method="ffill").fillna(CAPITAL)
        dd = (eq - eq.cummax()) / eq.cummax() * 100
        ax_dd.fill_between(dd.index, dd.values, 0, color="crimson", alpha=0.4)
        ax_dd.plot(dd.index, dd.values, color="crimson", linewidth=1)
        ax_dd.set_title(f"ドローダウン（最大 {best_result.max_drawdown_pct:.1f}%）")
        ax_dd.set_ylabel("DD (%)")
        ax_dd.set_xlabel("Date")
    ax_dd.grid(True, alpha=0.3)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    fig.autofmt_xdate()
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    out = plot_nissan_equity(Path("output/nissan_equity_growth.png"))
    print(f"Saved: {out.resolve()}")
