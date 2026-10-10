"""単一銘柄・押し目買い短期戦略バックテスト."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SingleTrade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str  # "take_profit" | "stop_loss" | "end_of_data"


@dataclass
class SingleBacktestResult:
    ticker: str
    trades: list[SingleTrade]
    equity_curve: pd.Series
    daily_returns: pd.Series
    total_return_pct: float
    buy_hold_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    num_trades: int
    num_signals: int
    avg_holding_days: float
    params: dict


def run_dip_buy_backtest(
    ohlc: pd.DataFrame,
    entry_drop_pct: float = 5.0,
    take_profit_pct: float = 3.0,
    stop_loss_pct: float = 4.0,
    initial_capital: float = 1_000_000,
    cost_bps: float = 10.0,
) -> SingleBacktestResult:
    """
    前日比 entry_drop_pct% 以上下落 → 終値で買い
    買値から +take_profit_pct% で利確、-stop_loss_pct% で損切（日中 High/Low 判定）
    """
    close = ohlc["Close"].squeeze().astype(float)
    high = ohlc["High"].squeeze().astype(float)
    low = ohlc["Low"].squeeze().astype(float)
    ticker = ohlc.attrs.get("ticker", "unknown")

    daily_ret = close.pct_change() * 100
    cost_rate = cost_bps / 10_000

    capital = initial_capital
    shares = 0.0
    entry_price = 0.0
    entry_idx: int | None = None
    entry_capital = 0.0

    trades: list[SingleTrade] = []
    equity: list[float] = []
    dates: list[pd.Timestamp] = []
    daily_rets: list[float] = []
    num_signals = 0

    tp_mult = 1 + take_profit_pct / 100
    sl_mult = 1 - stop_loss_pct / 100

    for t in range(1, len(ohlc)):
        date = ohlc.index[t]
        prev_capital = capital + (shares * float(close.iloc[t - 1]) if shares > 0 else 0)

        if shares > 0 and entry_idx is not None:
            tp_price = entry_price * tp_mult
            sl_price = entry_price * sl_mult
            day_high = float(high.iloc[t])
            day_low = float(low.iloc[t])

            exit_price: float | None = None
            exit_reason = ""

            if day_low <= sl_price:
                exit_price = sl_price
                exit_reason = "stop_loss"
            elif day_high >= tp_price:
                exit_price = tp_price
                exit_reason = "take_profit"

            if exit_price is not None:
                capital = shares * exit_price
                capital -= cost_rate * capital
                trade_pnl = capital - entry_capital
                trades.append(
                    SingleTrade(
                        entry_date=ohlc.index[entry_idx],
                        exit_date=date,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        pnl=trade_pnl,
                        pnl_pct=(exit_price / entry_price - 1) * 100,
                        holding_days=(date - ohlc.index[entry_idx]).days,
                        exit_reason=exit_reason,
                    )
                )
                shares = 0.0
                entry_idx = None

        if shares == 0 and float(daily_ret.iloc[t]) <= -entry_drop_pct:
            num_signals += 1
            entry_price = float(close.iloc[t])
            capital -= cost_rate * capital
            shares = capital / entry_price
            entry_capital = capital
            entry_idx = t
            capital = 0.0

        mtm = capital + shares * float(close.iloc[t])
        equity.append(mtm)
        dates.append(date)
        daily_rets.append((mtm - prev_capital) / prev_capital if prev_capital > 0 else 0.0)

    if shares > 0 and entry_idx is not None:
        exit_price = float(close.iloc[-1])
        capital = shares * exit_price
        capital -= cost_rate * capital
        trade_pnl = capital - entry_capital
        trades.append(
            SingleTrade(
                entry_date=ohlc.index[entry_idx],
                exit_date=ohlc.index[-1],
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=trade_pnl,
                pnl_pct=(exit_price / entry_price - 1) * 100,
                holding_days=(ohlc.index[-1] - ohlc.index[entry_idx]).days,
                exit_reason="end_of_data",
            )
        )
        equity[-1] = capital

    equity_series = pd.Series(equity, index=dates, name="equity")
    returns_series = pd.Series(daily_rets, index=dates, name="returns")

    total_return = (equity[-1] / initial_capital - 1) * 100
    bh_return = (float(close.iloc[-1]) / float(close.iloc[1]) - 1) * 100
    sharpe = (
        returns_series.mean() / returns_series.std() * np.sqrt(252)
        if returns_series.std() > 0
        else 0.0
    )
    rolling_max = equity_series.cummax()
    max_dd = float(((equity_series - rolling_max) / rolling_max).min() * 100)

    wins = sum(1 for tr in trades if tr.pnl > 0)
    win_rate = (wins / len(trades) * 100) if trades else 0.0
    avg_hold = float(np.mean([tr.holding_days for tr in trades])) if trades else 0.0

    return SingleBacktestResult(
        ticker=ticker,
        trades=trades,
        equity_curve=equity_series,
        daily_returns=returns_series,
        total_return_pct=float(total_return),
        buy_hold_return_pct=float(bh_return),
        sharpe_ratio=float(sharpe),
        max_drawdown_pct=max_dd,
        win_rate_pct=float(win_rate),
        num_trades=len(trades),
        num_signals=num_signals,
        avg_holding_days=avg_hold,
        params={
            "entry_drop_pct": entry_drop_pct,
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "cost_bps": cost_bps,
            "initial_capital": initial_capital,
        },
    )
