"""1000通りスイープ結果の分析."""

import pandas as pd
from itertools import product

df = pd.read_csv("output/sweep_1000/sweep_results.csv")
print(f"Total rows: {len(df)} (1000 combos x 3 tickers)")
print()

for ticker in df.ticker.unique():
    sub = df[(df.ticker == ticker) & (df.trades >= 20)].nlargest(5, "return_pct")
    name = sub.iloc[0]["name"] if len(sub) else ticker
    print(f"--- {name} (min 20 trades) top 5 ---")
    for _, r in sub.iterrows():
        print(
            f"  -{r.entry_drop:.0f}% +{r.take_profit:.0f}% -{r.stop_loss:.0f}% "
            f"-> {r.return_pct:+.1f}% ({r.trades:.0f}x, win {r.win_rate:.1f}%)"
        )
    print()

rows = []
for e, t, s in product(df.entry_drop.unique(), df.take_profit.unique(), df.stop_loss.unique()):
    sub = df[(df.entry_drop == e) & (df.take_profit == t) & (df.stop_loss == s)]
    if len(sub) != 3:
        continue
    if (sub["trades"] >= 20).all() and (sub["return_pct"] > 0).all():
        rows.append(
            {
                "e": e,
                "t": t,
                "s": s,
                "min": sub.return_pct.min(),
                "avg": sub.return_pct.mean(),
                "trades": sub.trades.sum(),
            }
        )

rdf = pd.DataFrame(rows).sort_values("avg", ascending=False)
print("=== All 3 positive (>=20 trades each) top 10 ===")
for _, r in rdf.head(10).iterrows():
    print(
        f"  -{r.e:.0f}% +{r.t:.0f}% -{r.s:.0f}% "
        f"min={r['min']:+.1f}% avg={r.avg:+.1f}% total={r.trades:.0f}x"
    )

print()
rdf2 = rdf[rdf.trades.between(60, 300)].sort_values("avg", ascending=False)
print("=== Robust band (60-300 total trades) top 8 ===")
for _, r in rdf2.head(8).iterrows():
    print(
        f"  -{r.e:.0f}% +{r.t:.0f}% -{r.s:.0f}% "
        f"min={r['min']:+.1f}% avg={r.avg:+.1f}% total={r.trades:.0f}x"
    )
