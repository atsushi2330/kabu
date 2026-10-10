import type { BacktestParams, BacktestResult, OhlcBar, Trade } from "./types";

function daysBetween(a: string, b: string): number {
  return Math.round(
    (new Date(b).getTime() - new Date(a).getTime()) / (1000 * 60 * 60 * 24),
  );
}

export function runDipBuyBacktest(
  bars: OhlcBar[],
  ticker: string,
  params: BacktestParams,
): BacktestResult {
  const { entryDropPct, takeProfitPct, stopLossPct, initialCapital, costBps = 10 } = params;
  const costRate = costBps / 10_000;
  const tpMult = 1 + takeProfitPct / 100;
  const slMult = 1 - stopLossPct / 100;

  let capital = initialCapital;
  let shares = 0;
  let entryPrice = 0;
  let entryIdx: number | null = null;
  let entryCapital = 0;

  const trades: Trade[] = [];
  const equityCurve: { date: string; equity: number }[] = [];

  for (let t = 1; t < bars.length; t++) {
    const bar = bars[t];
    const prevClose = bars[t - 1].close;
    const dailyRet = ((bar.close - prevClose) / prevClose) * 100;
    const prevEquity =
      shares > 0 ? shares * bars[t - 1].close : capital;

    if (shares > 0 && entryIdx !== null) {
      const tpPrice = entryPrice * tpMult;
      const slPrice = entryPrice * slMult;
      let exitPrice: number | null = null;
      let exitReason: Trade["exitReason"] = "stop_loss";

      if (bar.low <= slPrice) {
        exitPrice = slPrice;
        exitReason = "stop_loss";
      } else if (bar.high >= tpPrice) {
        exitPrice = tpPrice;
        exitReason = "take_profit";
      }

      if (exitPrice !== null) {
        capital = shares * exitPrice;
        capital -= costRate * capital;
        trades.push({
          entryDate: bars[entryIdx].date,
          exitDate: bar.date,
          entryPrice,
          exitPrice,
          pnl: capital - entryCapital,
          pnlPct: (exitPrice / entryPrice - 1) * 100,
          holdingDays: daysBetween(bars[entryIdx].date, bar.date),
          exitReason,
        });
        shares = 0;
        entryIdx = null;
      }
    }

    if (shares === 0 && dailyRet <= -entryDropPct) {
      entryPrice = bar.close;
      capital -= costRate * capital;
      shares = capital / entryPrice;
      entryCapital = capital;
      entryIdx = t;
      capital = 0;
    }

    const mtm = capital + shares * bar.close;
    equityCurve.push({ date: bar.date, equity: mtm });
  }

  if (shares > 0 && entryIdx !== null) {
    const last = bars[bars.length - 1];
    capital = shares * last.close;
    capital -= costRate * capital;
    trades.push({
      entryDate: bars[entryIdx].date,
      exitDate: last.date,
      entryPrice,
      exitPrice: last.close,
      pnl: capital - entryCapital,
      pnlPct: (last.close / entryPrice - 1) * 100,
      holdingDays: daysBetween(bars[entryIdx].date, last.date),
      exitReason: "end_of_data",
    });
    equityCurve[equityCurve.length - 1].equity = capital;
  }

  const finalEquity = equityCurve.length ? equityCurve[equityCurve.length - 1].equity : initialCapital;
  const bhReturn = ((bars[bars.length - 1].close / bars[1].close - 1) * 100);

  const dailyRets = equityCurve.map((p, i) =>
    i === 0 ? 0 : (p.equity - equityCurve[i - 1].equity) / equityCurve[i - 1].equity,
  );
  const mean = dailyRets.reduce((a, b) => a + b, 0) / dailyRets.length;
  const std = Math.sqrt(
    dailyRets.reduce((a, b) => a + (b - mean) ** 2, 0) / dailyRets.length,
  );
  const sharpe = std > 0 ? (mean / std) * Math.sqrt(252) : 0;

  let peak = initialCapital;
  let maxDd = 0;
  for (const p of equityCurve) {
    peak = Math.max(peak, p.equity);
    maxDd = Math.min(maxDd, (p.equity - peak) / peak);
  }

  const wins = trades.filter((t) => t.pnl > 0).length;

  return {
    ticker,
    trades,
    equityCurve,
    totalReturnPct: (finalEquity / initialCapital - 1) * 100,
    buyHoldReturnPct: bhReturn,
    sharpeRatio: sharpe,
    maxDrawdownPct: maxDd * 100,
    winRatePct: trades.length ? (wins / trades.length) * 100 : 0,
    numTrades: trades.length,
    avgHoldingDays: trades.length
      ? trades.reduce((a, t) => a + t.holdingDays, 0) / trades.length
      : 0,
    params,
    prices: bars,
  };
}
