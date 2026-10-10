"""バックテスト結果のグラフ."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .backtest import BacktestResult, Trade

plt.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLOR_LONG = "#1F8A65"
COLOR_SHORT = "#CF2D56"
COLOR_Z = "#3685BF"


def _fmt_yen(v: float) -> str:
    if abs(v) >= 10_000:
        return f"{v / 10_000:.1f}万"
    return f"{v / 1_000:.0f}k"


def _a_side(tr: Trade, kind: str) -> str:
    if kind == "entry":
        return "BUY" if tr.direction == "long" else "SELL"
    return "SELL" if tr.direction == "long" else "BUY"


def _b_side(tr: Trade, kind: str) -> str:
    if kind == "entry":
        return "SELL" if tr.direction == "long" else "BUY"
    return "BUY" if tr.direction == "long" else "SELL"


def _annotate_trade_on_price(
    ax,
    tr: Trade,
    ticker: str,
    leg: str,
    wins: int,
    losses: int,
) -> None:
    is_a = leg == "a"
    is_win = tr.pnl > 0
    entry_color = COLOR_LONG if tr.direction == "long" else COLOR_SHORT
    exit_color = COLOR_LONG if is_win else COLOR_SHORT

    if is_a:
        ep, xp = tr.entry_price_a, tr.exit_price_a
        ea, xa = tr.entry_amt_a, tr.exit_amt_a
        entry_side, exit_side = _a_side(tr, "entry"), _a_side(tr, "exit")
    else:
        ep, xp = tr.entry_price_b, tr.exit_price_b
        ea, xa = tr.entry_amt_b, tr.exit_amt_b
        entry_side, exit_side = _b_side(tr, "entry"), _b_side(tr, "exit")

    exit_dt = tr.exit_date_a if is_a and tr.exit_date_a else (tr.exit_date_b if not is_a and tr.exit_date_b else tr.exit_date)
    ax.scatter(tr.entry_date, ep, marker="^" if entry_side == "BUY" else "v",
               s=90, color=entry_color, edgecolors="white", linewidths=0.6, zorder=5)
    ax.scatter(exit_dt, xp, marker="X" if not is_win else "o",
               s=70 if not is_win else 60, color=exit_color, edgecolors="white", linewidths=0.6, zorder=5)

    y_off = ep * 0.02
    ax.annotate(
        f"{entry_side} {_fmt_yen(ea)}\n@{ep:,.0f}円",
        xy=(tr.entry_date, ep),
        xytext=(0, 12 if entry_side == "BUY" else -28),
        textcoords="offset points",
        fontsize=6.5, ha="center", color=entry_color,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor=entry_color, linewidth=0.5),
        arrowprops=dict(arrowstyle="-", color=entry_color, lw=0.5),
    )
    ax.annotate(
        f"{exit_side} {_fmt_yen(xa)}\n@{xp:,.0f}円",
        xy=(exit_dt, xp),
        xytext=(0, -28 if exit_side == "SELL" else 12),
        textcoords="offset points",
        fontsize=6.5, ha="center", color=exit_color,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor=exit_color, linewidth=0.5),
        arrowprops=dict(arrowstyle="-", color=exit_color, lw=0.5),
    )


def plot_backtest(
    prices: pd.DataFrame,
    result: BacktestResult,
    output_path: Path,
    pair_name: str | None = None,
) -> Path:
    title = pair_name or f"{result.ticker_a} x {result.ticker_b}"
    a, b = result.ticker_a, result.ticker_b
    p = result.params
    entry_z = p["entry_z"]
    exit_z = p.get("exit_z")
    exit_leg_pct = p.get("exit_leg_pct")
    individual = p.get("individual_leg_exit")
    take_profit = p.get("take_profit_leg_pct", 4.0)
    stop_loss = p.get("stop_loss_leg_pct", 3.0)
    z = result.zscore_series

    wins = sum(1 for tr in result.trades if tr.pnl > 0)
    losses = len(result.trades) - wins

    fig = plt.figure(figsize=(16, 20))
    gs = fig.add_gridspec(6, 1, height_ratios=[1.8, 1.6, 1.6, 0.9, 0.9, 1.2], hspace=0.42)
    ax_z = fig.add_subplot(gs[0])
    ax_a = fig.add_subplot(gs[1], sharex=ax_z)
    ax_b = fig.add_subplot(gs[2], sharex=ax_z)
    ax_pos = fig.add_subplot(gs[3], sharex=ax_z)
    ax_eq = fig.add_subplot(gs[4], sharex=ax_z)
    ax_tbl = fig.add_subplot(gs[5])
    ax_tbl.axis("off")

    fig.suptitle(f"Trade Timing + Amounts: {title}", fontsize=14, fontweight="bold")

    # --- Z-score ---
    ax_z.plot(z.index, z.values, color=COLOR_Z, linewidth=1.0, zorder=2)
    ax_z.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax_z.axhline(entry_z, color=COLOR_SHORT, linewidth=1, linestyle=":", alpha=0.8)
    ax_z.axhline(-entry_z, color=COLOR_LONG, linewidth=1, linestyle=":", alpha=0.8)
    if exit_z is not None and exit_leg_pct is None and not individual:
        ax_z.axhline(exit_z, color="#999", linewidth=0.8, linestyle="--", alpha=0.7)
        ax_z.axhline(-exit_z, color="#999", linewidth=0.8, linestyle="--", alpha=0.7)

    for tr in result.trades:
        is_long = tr.direction == "long"
        is_win = tr.pnl > 0
        ec = COLOR_LONG if is_long else COLOR_SHORT
        xc = COLOR_LONG if is_win else COLOR_SHORT
        ax_z.scatter(tr.entry_date, tr.entry_z, marker="^" if is_long else "v", s=80, color=ec, zorder=5)
        ax_z.scatter(tr.exit_date, tr.exit_z, marker="X" if not is_win else "o", s=70, color=xc, zorder=5)

    if individual:
        exit_label = f"Exit each +{take_profit}% / stop -{stop_loss}% (individual)"
    elif exit_leg_pct:
        exit_label = f"Exit leg +{exit_leg_pct}%"
    else:
        exit_label = f"Exit |Z|<{exit_z}"
    ax_z.set_title(f"Z-score  |  Entry |Z|>{entry_z}  /  {exit_label}  |  W{wins}/L{losses}")
    ax_z.set_ylabel("Z")
    ax_z.grid(True, alpha=0.3)

    # --- Stock A price ---
    series_a = prices[a].reindex(z.index, method="ffill")
    ax_a.plot(series_a.index, series_a.values, color="#E67E22", linewidth=1.0, label=a)
    for tr in result.trades:
        _annotate_trade_on_price(ax_a, tr, a, "a", wins, losses)
    ax_a.set_ylabel("Price (JPY)")
    ax_a.set_title(f"{a}  —  entry/exit amount & price")
    ax_a.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_a.grid(True, alpha=0.3)

    # --- Stock B price ---
    series_b = prices[b].reindex(z.index, method="ffill")
    ax_b.plot(series_b.index, series_b.values, color="#8E44AD", linewidth=1.0, label=b)
    for tr in result.trades:
        _annotate_trade_on_price(ax_b, tr, b, "b", wins, losses)
    ax_b.set_ylabel("Price (JPY)")
    ax_b.set_title(f"{b}  —  entry/exit amount & price")
    ax_b.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_b.grid(True, alpha=0.3)

    # --- Position ---
    pos_series = pd.Series(0.0, index=z.index)
    for tr in result.trades:
        mask = (pos_series.index >= tr.entry_date) & (pos_series.index <= tr.exit_date)
        pos_series.loc[mask] = 1.0 if tr.direction == "long" else -1.0
    ax_pos.fill_between(pos_series.index, 0, pos_series.values, step="post", alpha=0.35,
                        where=pos_series > 0, color=COLOR_LONG)
    ax_pos.fill_between(pos_series.index, 0, pos_series.values, step="post", alpha=0.35,
                        where=pos_series < 0, color=COLOR_SHORT)
    ax_pos.set_yticks([-1, 0, 1])
    ax_pos.set_yticklabels(["Short", "Flat", "Long"])
    ax_pos.set_title("Position")
    ax_pos.grid(True, alpha=0.3)

    # --- Equity ---
    ax_eq.plot(result.equity_curve.index, result.equity_curve.values, color=COLOR_Z, linewidth=1.2)
    ax_eq.axhline(p["initial_capital"], color="gray", linestyle="--", linewidth=0.8)
    ax_eq.set_ylabel("Capital")
    ax_eq.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.2f}M"))
    ax_eq.set_title("Equity")
    ax_eq.grid(True, alpha=0.3)

    # --- Table with amounts ---
    display = result.trades if len(result.trades) <= 10 else result.trades[-10:]
    rows = []
    for tr in display:
        if tr.direction == "long":
            a_in, b_in = f"BUY {_fmt_yen(tr.entry_amt_a)}", f"SELL {_fmt_yen(tr.entry_amt_b)}"
            a_out, b_out = f"SELL {_fmt_yen(tr.exit_amt_a)}", f"BUY {_fmt_yen(tr.exit_amt_b)}"
        else:
            a_in, b_in = f"SELL {_fmt_yen(tr.entry_amt_a)}", f"BUY {_fmt_yen(tr.entry_amt_b)}"
            a_out, b_out = f"BUY {_fmt_yen(tr.exit_amt_a)}", f"SELL {_fmt_yen(tr.exit_amt_b)}"
        a_out_dt = tr.exit_date_a.strftime("%m/%d") if tr.exit_date_a else "-"
        b_out_dt = tr.exit_date_b.strftime("%m/%d") if tr.exit_date_b else "-"
        rows.append([
            tr.entry_date.strftime("%m/%d"),
            f"A:{a_out_dt} B:{b_out_dt}",
            tr.direction[:1].upper(),
            a_in,
            b_in,
            a_out,
            b_out,
            f"{tr.pnl:+,.0f}",
        ])

    if rows:
        table = ax_tbl.table(
            cellText=rows,
            colLabels=["In", "Exit A/B", "D", "A entry", "B entry", "A exit", "B exit", "PnL"],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.35)
        for row_idx, tr in enumerate(display, start=1):
            if tr.pnl <= 0:
                for col_idx in range(8):
                    table[(row_idx, col_idx)].set_facecolor("#FDE8EC")

    footer = (
        f"Return {result.total_return_pct:+.2f}%  |  Sharpe {result.sharpe_ratio:.2f}  |  "
        f"MaxDD {result.max_drawdown_pct:.2f}%  |  "
        f"Sizing: 50% capital each leg (dollar neutral)"
    )
    fig.text(0.5, 0.003, footer, ha="center", fontsize=9, color="#444")

    for ax in (ax_z, ax_a, ax_b, ax_pos):
        plt.setp(ax.get_xticklabels(), visible=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
