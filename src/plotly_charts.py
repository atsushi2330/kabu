"""Plotly チャート生成."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .single_backtest import SingleBacktestResult


def make_equity_chart(
    ohlc: pd.DataFrame,
    result: SingleBacktestResult,
    name: str,
) -> go.Figure:
    close = ohlc["Close"].squeeze()
    capital = result.params["initial_capital"]
    eq = result.equity_curve.reindex(close.index, method="ffill").fillna(capital)
    bh = close / close.iloc[1] * capital

    p = result.params
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.65, 0.35],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    fig.add_trace(
        go.Scatter(x=eq.index, y=eq, name="資産", line=dict(color="#2563eb", width=2)),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=bh.index, y=bh, name="B&H", line=dict(color="#9ca3af", width=1.5, dash="dot")),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=close.index,
            y=close,
            name="株価",
            line=dict(color="#7c3aed", width=1.2),
            opacity=0.7,
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    entry_win_x, entry_win_y, exit_win_x, exit_win_y = [], [], [], []
    entry_loss_x, entry_loss_y, exit_loss_x, exit_loss_y = [], [], [], []
    for tr in result.trades:
        ed = tr.entry_date
        xd = tr.exit_date
        ey = float(eq.reindex([ed], method="ffill").iloc[0])
        xy = float(eq.reindex([xd], method="ffill").iloc[0])
        if tr.pnl > 0:
            entry_win_x.append(ed)
            entry_win_y.append(ey)
            exit_win_x.append(xd)
            exit_win_y.append(xy)
        else:
            entry_loss_x.append(ed)
            entry_loss_y.append(ey)
            exit_loss_x.append(xd)
            exit_loss_y.append(xy)

    if entry_win_x:
        fig.add_trace(
            go.Scatter(
                x=entry_win_x,
                y=entry_win_y,
                mode="markers",
                name="▲ 買い（勝ち）",
                marker=dict(symbol="triangle-up", size=9, color="#16a34a"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=exit_win_x,
                y=exit_win_y,
                mode="markers",
                name="▼ 売り（勝ち）",
                marker=dict(symbol="triangle-down", size=9, color="#16a34a"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
    if entry_loss_x:
        fig.add_trace(
            go.Scatter(
                x=entry_loss_x,
                y=entry_loss_y,
                mode="markers",
                name="▲ 買い（負け）",
                marker=dict(symbol="triangle-up", size=9, color="#dc2626"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=exit_loss_x,
                y=exit_loss_y,
                mode="markers",
                name="▼ 売り（負け）",
                marker=dict(symbol="triangle-down", size=9, color="#dc2626"),
            ),
            row=1,
            col=1,
            secondary_y=False,
        )

    dd = (eq - eq.cummax()) / eq.cummax() * 100
    fig.add_trace(
        go.Scatter(x=dd.index, y=dd, name="DD", fill="tozeroy", line=dict(color="#dc2626", width=1)),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=(
            f"{name} ({result.ticker}) — "
            f"-{p['entry_drop_pct']:.0f}% / +{p['take_profit_pct']:.0f}% / -{p['stop_loss_pct']:.0f}% "
            f"| リターン {result.total_return_pct:+.1f}% | 勝率 {result.win_rate_pct:.1f}%"
        ),
        height=680,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=60, r=60, t=80, b=40),
    )
    fig.update_yaxes(title_text="資産 (円)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="株価 (円)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="DD (%)", row=2, col=1)
    fig.update_xaxes(title_text="日付", row=2, col=1)

    return fig


def trades_to_dataframe(result: SingleBacktestResult) -> pd.DataFrame:
    rows = []
    for tr in result.trades:
        rows.append(
            {
                "entry_date": tr.entry_date.date(),
                "exit_date": tr.exit_date.date(),
                "entry_price": tr.entry_price,
                "exit_price": tr.exit_price,
                "pnl_pct": tr.pnl_pct,
                "pnl": tr.pnl,
                "holding_days": tr.holding_days,
                "exit_reason": tr.exit_reason,
            }
        )
    return pd.DataFrame(rows)
