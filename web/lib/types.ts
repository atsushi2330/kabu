export interface OhlcBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Trade {
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPct: number;
  holdingDays: number;
  exitReason: "take_profit" | "stop_loss" | "end_of_data";
}

export interface BacktestParams {
  entryDropPct: number;
  takeProfitPct: number;
  stopLossPct: number;
  initialCapital: number;
  costBps?: number;
}

export interface BacktestResult {
  ticker: string;
  trades: Trade[];
  equityCurve: { date: string; equity: number }[];
  totalReturnPct: number;
  buyHoldReturnPct: number;
  sharpeRatio: number;
  maxDrawdownPct: number;
  winRatePct: number;
  numTrades: number;
  avgHoldingDays: number;
  params: BacktestParams;
  prices: OhlcBar[];
}
