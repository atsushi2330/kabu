"""バックテスト結果のレポート."""

from __future__ import annotations

from .backtest import BacktestResult


def _fmt(v: float) -> str:
    return f"{v/10_000:.1f}万" if v >= 10_000 else f"{v/1_000:.0f}k"


def format_backtest_report(result: BacktestResult, pair_name: str | None = None) -> str:
    title = pair_name or f"{result.ticker_a} x {result.ticker_b}"
    p = result.params

    lines = [
        "",
        f"=== Backtest: {title} ===",
        "",
        "[Parameters]",
        f"  Lookback     : {p['lookback']} days",
        f"  Z window     : {p['z_window']} days",
        f"  Entry Z      : +/- {p['entry_z']}",
    ]
    if p.get("individual_leg_exit"):
        lines += [
            f"  Exit         : each leg +{p['take_profit_leg_pct']}% favorable (individual)",
            f"  Stop         : each leg -{p['stop_loss_leg_pct']}% adverse (individual)",
            f"  Max holding  : {p.get('max_holding_days')} days (force close both)",
        ]
    elif p.get("exit_leg_pct") is not None:
        lines += [
            f"  Exit legs    : A&B each >= {p['exit_leg_pct']}% favorable ({p.get('exit_mode', 'and')})",
            f"  Stop legs    : {p.get('stop_leg_pct') or p['exit_leg_pct'] * 2}% adverse",
            f"  Max holding  : {p.get('max_holding_days')} days",
        ]
    else:
        lines += [
            f"  Exit Z       : +/- {p['exit_z']}",
            f"  Stop Z       : +/- {p['stop_z']}",
        ]
    lines += [
        f"  Cost         : {p['cost_bps']} bps / leg",
        f"  Capital      : {p['initial_capital']:,.0f} JPY",
    ]
    lines += [
        "",
        "[Performance]",
        f"  Total return : {result.total_return_pct:+.2f} %",
        f"  Sharpe ratio : {result.sharpe_ratio:.2f}",
        f"  Max drawdown : {result.max_drawdown_pct:.2f} %",
        f"  Win rate     : {result.win_rate_pct:.1f} %",
        f"  Trades       : {result.num_trades}",
        f"  Avg holding  : {result.avg_holding_days:.1f} days",
        "",
    ]

    if result.trades:
        lines.append("[Recent trades (last 5)]")
        for tr in result.trades[-5:]:
            if tr.direction == "long":
                legs = (
                    f"A BUY {_fmt(tr.entry_amt_a)}->SELL {_fmt(tr.exit_amt_a)}  "
                    f"B SELL {_fmt(tr.entry_amt_b)}->BUY {_fmt(tr.exit_amt_b)}"
                )
            else:
                legs = (
                    f"A SELL {_fmt(tr.entry_amt_a)}->BUY {_fmt(tr.exit_amt_a)}  "
                    f"B BUY {_fmt(tr.entry_amt_b)}->SELL {_fmt(tr.exit_amt_b)}"
                )
            lines.append(
                f"  {tr.entry_date.date()} -> {tr.exit_date.date()}  "
                f"{tr.direction:5s}  Z:{tr.entry_z:+.2f}->{tr.exit_z:+.2f}  "
                f"PnL:{tr.pnl:+,.0f}  ({tr.holding_days}d)"
            )
            lines.append(f"    {legs}")
        lines.append("")

    return "\n".join(lines)
