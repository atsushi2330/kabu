"""Zスコア平均回帰戦略のバックテスト（ルックアヘッド回避）."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: str  # "long" | "short"
    entry_z: float
    exit_z: float
    pnl: float
    holding_days: int
    entry_price_a: float = 0.0
    entry_price_b: float = 0.0
    exit_price_a: float = 0.0
    exit_price_b: float = 0.0
    n_a: float = 0.0
    n_b: float = 0.0
    exit_date_a: pd.Timestamp | None = None
    exit_date_b: pd.Timestamp | None = None

    @property
    def entry_amt_a(self) -> float:
        return abs(self.n_a) * self.entry_price_a

    @property
    def entry_amt_b(self) -> float:
        return abs(self.n_b) * self.entry_price_b

    @property
    def exit_amt_a(self) -> float:
        return abs(self.n_a) * self.exit_price_a

    @property
    def exit_amt_b(self) -> float:
        return abs(self.n_b) * self.exit_price_b


@dataclass
class BacktestResult:
    ticker_a: str
    ticker_b: str
    trades: list[Trade]
    equity_curve: pd.Series
    daily_returns: pd.Series
    zscore_series: pd.Series
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    num_trades: int
    avg_holding_days: float
    params: dict


def _estimate_beta(prices: pd.DataFrame, end_idx: int, lookback: int) -> tuple[float, float]:
    window = prices.iloc[end_idx - lookback : end_idx]
    ticker_a, ticker_b = window.columns[0], window.columns[1]
    x = sm.add_constant(window[ticker_b])
    model = sm.OLS(window[ticker_a], x).fit()
    return float(model.params["const"]), float(model.params[ticker_b])


def _rolling_zscore(spread: pd.Series, end_idx: int, z_window: int) -> float:
    window = spread.iloc[max(0, end_idx - z_window + 1) : end_idx + 1]
    if len(window) < 20 or window.std() == 0:
        return float("nan")
    return float((window.iloc[-1] - window.mean()) / window.std())


def _leg_favorable_pct(
    position: int,
    entry_price_a: float,
    entry_price_b: float,
    price_a: float,
    price_b: float,
) -> tuple[float, float]:
    """各レッグの「お得方向」への変動率（%）."""
    if position == 1:
        a_pct = (price_a / entry_price_a - 1) * 100
        b_pct = (entry_price_b / price_b - 1) * 100
    else:
        a_pct = (entry_price_a / price_a - 1) * 100
        b_pct = (price_b / entry_price_b - 1) * 100
    return a_pct, b_pct


def _position_sizes(capital: float, price_a: float, price_b: float, beta: float, direction: int) -> tuple[float, float]:
    """ドルニュートラル（金額半々）."""
    half = capital / 2
    if direction == 1:
        n_a = half / price_a
        n_b = -(half / price_b)
    else:
        n_a = -(half / price_a)
        n_b = half / price_b
    return n_a, n_b


def run_backtest(
    prices: pd.DataFrame,
    lookback: int = 252,
    z_window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 1.0,
    stop_z: float = 4.0,
    exit_leg_pct: float | None = None,
    stop_leg_pct: float | None = None,
    exit_mode: str = "and",
    individual_leg_exit: bool = False,
    take_profit_leg_pct: float = 4.0,
    stop_loss_leg_pct: float = 3.0,
    max_holding_days: int | None = 60,
    initial_capital: float = 1_000_000,
    cost_bps: float = 10.0,
    beta_rebalance: int = 21,
) -> BacktestResult:
    a, b = prices.columns[0], prices.columns[1]
    n = len(prices)
    if n <= lookback + z_window:
        raise ValueError("データが短すぎます")

    position = 0
    entry_idx: int | None = None
    entry_z_val = 0.0
    entry_capital = 0.0
    entry_price_a = 0.0
    entry_price_b = 0.0
    n_a = 0.0
    n_b = 0.0
    orig_n_a = 0.0
    orig_n_b = 0.0
    leg_a_open = False
    leg_b_open = False
    leg_exit_price_a = 0.0
    leg_exit_price_b = 0.0
    leg_exit_date_a: pd.Timestamp | None = None
    leg_exit_date_b: pd.Timestamp | None = None

    capital = initial_capital
    trades: list[Trade] = []
    equity: list[float] = []
    dates: list[pd.Timestamp] = []
    daily_rets: list[float] = []
    zscores: list[float] = []

    alpha, beta = _estimate_beta(prices, lookback, lookback)
    last_beta_update = lookback
    cost_rate = cost_bps / 10_000

    def finalize_trade(t: int, z: float) -> None:
        nonlocal position, capital, entry_idx, entry_capital
        nonlocal n_a, n_b, leg_a_open, leg_b_open
        if position == 0 or entry_idx is None:
            return
        exit_dt = prices.index[t]
        if leg_exit_date_a and leg_exit_date_b:
            exit_dt = max(leg_exit_date_a, leg_exit_date_b)
        trade_pnl = capital - entry_capital
        trades.append(
            Trade(
                entry_date=prices.index[entry_idx],
                exit_date=exit_dt,
                direction="long" if position == 1 else "short",
                entry_z=entry_z_val,
                exit_z=z,
                pnl=trade_pnl,
                holding_days=(exit_dt - prices.index[entry_idx]).days,
                entry_price_a=entry_price_a,
                entry_price_b=entry_price_b,
                exit_price_a=leg_exit_price_a,
                exit_price_b=leg_exit_price_b,
                n_a=orig_n_a,
                n_b=orig_n_b,
                exit_date_a=leg_exit_date_a,
                exit_date_b=leg_exit_date_b,
            )
        )
        position = 0
        entry_idx = None
        leg_a_open = leg_b_open = False
        n_a = n_b = 0.0

    def close_leg(t: int, leg: str, price: float) -> None:
        nonlocal capital, n_a, n_b, leg_a_open, leg_b_open
        nonlocal leg_exit_price_a, leg_exit_price_b, leg_exit_date_a, leg_exit_date_b
        capital -= cost_rate * capital
        if leg == "a":
            leg_a_open = False
            n_a = 0.0
            leg_exit_price_a = price
            leg_exit_date_a = prices.index[t]
        else:
            leg_b_open = False
            n_b = 0.0
            leg_exit_price_b = price
            leg_exit_date_b = prices.index[t]

    def close_both_legs(t: int, z: float) -> None:
        nonlocal leg_a_open, leg_b_open
        price_a = float(prices[a].iloc[t])
        price_b = float(prices[b].iloc[t])
        if leg_a_open:
            close_leg(t, "a", price_a)
        if leg_b_open:
            close_leg(t, "b", price_b)
        finalize_trade(t, z)

    for t in range(lookback, n):
        date = prices.index[t]

        if t - last_beta_update >= beta_rebalance:
            alpha, beta = _estimate_beta(prices, t, lookback)
            last_beta_update = t

        spread_hist = prices[a].iloc[: t + 1] - alpha - beta * prices[b].iloc[: t + 1]
        z = _rolling_zscore(spread_hist, t, z_window)

        prev_capital = capital
        pnl_today = 0.0

        if position != 0 and t > 0:
            d_a = float(prices[a].iloc[t] - prices[a].iloc[t - 1])
            d_b = float(prices[b].iloc[t] - prices[b].iloc[t - 1])
            if leg_a_open:
                pnl_today += n_a * d_a
            if leg_b_open:
                pnl_today += n_b * d_b

        capital += pnl_today

        if position != 0 and entry_idx is not None:
            price_a = float(prices[a].iloc[t])
            price_b = float(prices[b].iloc[t])
            holding = t - entry_idx

            if individual_leg_exit:
                a_pct, b_pct = _leg_favorable_pct(position, entry_price_a, entry_price_b, price_a, price_b)

                if leg_a_open and (a_pct >= take_profit_leg_pct or a_pct <= -stop_loss_leg_pct):
                    close_leg(t, "a", price_a)
                if leg_b_open and (b_pct >= take_profit_leg_pct or b_pct <= -stop_loss_leg_pct):
                    close_leg(t, "b", price_b)

                if max_holding_days is not None and holding >= max_holding_days:
                    close_both_legs(t, z if not np.isnan(z) else 0.0)
                elif not leg_a_open and not leg_b_open:
                    finalize_trade(t, z if not np.isnan(z) else 0.0)

            elif exit_leg_pct is not None:
                stop_pct = stop_leg_pct if stop_leg_pct is not None else exit_leg_pct * 2
                a_pct, b_pct = _leg_favorable_pct(position, entry_price_a, entry_price_b, price_a, price_b)
                if exit_mode == "and":
                    should_exit = a_pct >= exit_leg_pct and b_pct >= exit_leg_pct
                else:
                    should_exit = a_pct >= exit_leg_pct or b_pct >= exit_leg_pct
                if not should_exit and stop_pct is not None:
                    should_exit = a_pct <= -stop_pct or b_pct <= -stop_pct
                if should_exit or (max_holding_days is not None and holding >= max_holding_days):
                    close_both_legs(t, z if not np.isnan(z) else 0.0)

            elif not np.isnan(z):
                if abs(z) < exit_z:
                    close_both_legs(t, z)
                elif position == 1 and z <= -stop_z:
                    close_both_legs(t, z)
                elif position == -1 and z >= stop_z:
                    close_both_legs(t, z)

        if not np.isnan(z) and position == 0:
            if z < -entry_z:
                cost = cost_rate * capital * 2
                capital -= cost
                position = 1
                entry_idx = t
                entry_z_val = z
                entry_capital = capital
                price_a = float(prices[a].iloc[t])
                price_b = float(prices[b].iloc[t])
                entry_price_a, entry_price_b = price_a, price_b
                n_a, n_b = _position_sizes(capital, price_a, price_b, beta, 1)
                orig_n_a, orig_n_b = n_a, n_b
                leg_a_open = leg_b_open = True
                leg_exit_date_a = leg_exit_date_b = None
                leg_exit_price_a = leg_exit_price_b = 0.0
            elif z > entry_z:
                cost = cost_rate * capital * 2
                capital -= cost
                position = -1
                entry_idx = t
                entry_z_val = z
                entry_capital = capital
                price_a = float(prices[a].iloc[t])
                price_b = float(prices[b].iloc[t])
                entry_price_a, entry_price_b = price_a, price_b
                n_a, n_b = _position_sizes(capital, price_a, price_b, beta, -1)
                orig_n_a, orig_n_b = n_a, n_b
                leg_a_open = leg_b_open = True
                leg_exit_date_a = leg_exit_date_b = None
                leg_exit_price_a = leg_exit_price_b = 0.0

        equity.append(capital)
        dates.append(date)
        zscores.append(float(z) if not np.isnan(z) else np.nan)
        daily_rets.append((capital - prev_capital) / prev_capital if prev_capital > 0 else 0.0)

    if position != 0 and entry_idx is not None:
        z = _rolling_zscore(
            prices[a].iloc[:n] - alpha - beta * prices[b].iloc[:n],
            n - 1,
            z_window,
        )
        close_both_legs(n - 1, z if not np.isnan(z) else 0.0)

    equity_series = pd.Series(equity, index=dates, name="equity")
    returns_series = pd.Series(daily_rets, index=dates, name="returns")
    zscore_series = pd.Series(zscores, index=dates, name="zscore")

    total_return = (equity[-1] / initial_capital - 1) * 100
    sharpe = (
        returns_series.mean() / returns_series.std() * np.sqrt(252)
        if returns_series.std() > 0
        else 0.0
    )
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_dd = float(drawdown.min() * 100)

    wins = sum(1 for tr in trades if tr.pnl > 0)
    win_rate = (wins / len(trades) * 100) if trades else 0.0
    avg_hold = float(np.mean([tr.holding_days for tr in trades])) if trades else 0.0

    return BacktestResult(
        ticker_a=a,
        ticker_b=b,
        trades=trades,
        equity_curve=equity_series,
        daily_returns=returns_series,
        zscore_series=zscore_series,
        total_return_pct=float(total_return),
        sharpe_ratio=float(sharpe),
        max_drawdown_pct=max_dd,
        win_rate_pct=float(win_rate),
        num_trades=len(trades),
        avg_holding_days=avg_hold,
        params={
            "lookback": lookback,
            "z_window": z_window,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "stop_z": stop_z,
            "exit_leg_pct": exit_leg_pct,
            "stop_leg_pct": stop_leg_pct,
            "exit_mode": exit_mode,
            "individual_leg_exit": individual_leg_exit,
            "take_profit_leg_pct": take_profit_leg_pct,
            "stop_loss_leg_pct": stop_loss_leg_pct,
            "max_holding_days": max_holding_days,
            "cost_bps": cost_bps,
            "initial_capital": initial_capital,
        },
    )
