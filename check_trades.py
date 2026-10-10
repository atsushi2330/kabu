from src.fetch import fetch_prices
from src.backtest import run_backtest

prices = fetch_prices(["8411.T", "8308.T"], years=5)
r = run_backtest(prices)
wins = [t for t in r.trades if t.pnl > 0]
losses = [t for t in r.trades if t.pnl <= 0]
init = r.params["initial_capital"]
print(f"Total trades: {len(r.trades)}")
print(f"Wins: {len(wins)}  Losses: {len(losses)}")
print(f"Sum trade PnL: {sum(t.pnl for t in r.trades):,.0f}")
print(f"Equity change: {r.equity_curve.iloc[-1] - init:,.0f}")
print("\nLOSSES:")
for t in losses:
    print(
        f"  {t.entry_date.date()} -> {t.exit_date.date()}  {t.direction:5s}  "
        f"PnL {t.pnl:+,.0f}  Z {t.entry_z:+.2f}->{t.exit_z:+.2f}"
    )
