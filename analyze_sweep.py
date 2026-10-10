"""スイープ結果の横断分析."""

import pandas as pd
from itertools import product

df = pd.read_csv("output/sweep_results.csv")
rows = []
for e, t, s in product(df.entry_drop.unique(), df.take_profit.unique(), df.stop_loss.unique()):
    sub = df[(df.entry_drop == e) & (df.take_profit == t) & (df.stop_loss == s)]
    if len(sub) != 3:
        continue
    if (sub["trades"] >= 10).all() and (sub["return_pct"] > 0).all():
        rows.append(
            {
                "entry": e,
                "tp": t,
                "sl": s,
                "min_ret": sub.return_pct.min(),
                "avg_ret": sub.return_pct.mean(),
                "total_trades": sub.trades.sum(),
            }
        )

rdf = pd.DataFrame(rows).sort_values("avg_ret", ascending=False)
print("=== Positive on ALL 3 tickers (>=10 trades each) ===")
print(f"{'Entry':>6} {'TP':>4} {'SL':>4} {'MinRet':>8} {'AvgRet':>8} {'Trades':>7}")
print("-" * 45)
for _, r in rdf.head(15).iterrows():
    print(
        f"-{r['entry']:4.0f}% +{r['tp']:3.0f}% -{r['sl']:3.0f}% "
        f"{r['min_ret']:+7.1f}% {r['avg_ret']:+7.1f}% {r['total_trades']:7.0f}"
    )

print()
rdf2 = rdf[rdf.total_trades.between(80, 250)].sort_values("avg_ret", ascending=False)
print("=== Balanced (80-250 total trades) ===")
for _, r in rdf2.head(8).iterrows():
    print(
        f"-{r['entry']:4.0f}% +{r['tp']:3.0f}% -{r['sl']:3.0f}% "
        f"min={r['min_ret']:+.1f}% avg={r['avg_ret']:+.1f}% trades={r['total_trades']:.0f}"
    )
