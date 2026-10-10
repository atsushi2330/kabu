"use client";

import { useMemo, useState } from "react";
import { runDipBuyBacktest } from "@/lib/backtest";
import { ALL_TICKERS, TICKER_PRESETS } from "@/lib/presets";
import type { BacktestResult, OhlcBar } from "@/lib/types";
import EquityChart from "./EquityChart";

export default function BacktestApp() {
  const [preset, setPreset] = useState<string>("銀行");
  const [selected, setSelected] = useState<string[]>(["8411.T", "8308.T"]);
  const [entryDrop, setEntryDrop] = useState(5);
  const [takeProfit, setTakeProfit] = useState(10);
  const [stopLoss, setStopLoss] = useState(3);
  const [years, setYears] = useState(5);
  const [capital, setCapital] = useState(1_000_000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<BacktestResult[]>([]);

  const tickersInPreset = useMemo(
    () => Object.keys(TICKER_PRESETS[preset] ?? {}),
    [preset],
  );

  async function run() {
    if (!selected.length) {
      setError("銘柄を1つ以上選んで");
      return;
    }
    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const out: BacktestResult[] = [];
      for (let i = 0; i < selected.length; i++) {
        const ticker = selected[i];
        if (i > 0) await new Promise((r) => setTimeout(r, 2000));

        const res = await fetch(`/api/ohlc?ticker=${encodeURIComponent(ticker)}&years=${years}`);
        let body: { error?: string; bars?: OhlcBar[] } = {};
        try {
          body = await res.json();
        } catch {
          throw new Error(
            res.status === 429
              ? "Yahoo Finance のアクセス制限。30秒〜1分待って再実行してください。"
              : `${ticker} の応答が不正です`,
          );
        }
        if (!res.ok) {
          throw new Error(body.error ?? `${ticker} 取得失敗 (${res.status})`);
        }
        if (!body.bars?.length) {
          throw new Error(`${ticker} のデータが空です`);
        }
        out.push(
          runDipBuyBacktest(body.bars, ticker, {
            entryDropPct: entryDrop,
            takeProfitPct: takeProfit,
            stopLossPct: stopLoss,
            initialCapital: capital,
          }),
        );
      }
      setResults(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setLoading(false);
    }
  }

  function toggleTicker(t: string) {
    setSelected((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  }

  function downloadCsv(result: BacktestResult) {
    const header = "entry_date,exit_date,entry_price,exit_price,pnl_pct,pnl,holding_days,exit_reason\n";
    const rows = result.trades
      .map(
        (t) =>
          `${t.entryDate},${t.exitDate},${t.entryPrice},${t.exitPrice},${t.pnlPct},${t.pnl},${t.holdingDays},${t.exitReason}`,
      )
      .join("\n");
    const blob = new Blob(["\uFEFF" + header + rows], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `trades_${result.ticker.replace(".", "_")}.csv`;
    a.click();
  }

  return (
    <div className="layout">
      <aside className="panel">
        <h2>設定</h2>
        <label>プリセット</label>
        <select
          value={preset}
          onChange={(e) => {
            const p = e.target.value;
            setPreset(p);
            setSelected(Object.keys(TICKER_PRESETS[p] ?? {}).slice(0, 2));
          }}
        >
          {Object.keys(TICKER_PRESETS).map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>

        <label>銘柄（複数可）</label>
        <div className="ticker-list">
          {tickersInPreset.map((t) => (
            <label key={t}>
              <input
                type="checkbox"
                checked={selected.includes(t)}
                onChange={() => toggleTicker(t)}
              />
              {TICKER_PRESETS[preset][t]} ({t})
            </label>
          ))}
        </div>

        <label>エントリー (-%)</label>
        <input type="number" min={1} max={15} value={entryDrop} onChange={(e) => setEntryDrop(+e.target.value)} />

        <label>利確 (+%)</label>
        <input type="number" min={1} max={20} value={takeProfit} onChange={(e) => setTakeProfit(+e.target.value)} />

        <label>損切 (-%)</label>
        <input type="number" min={1} max={15} value={stopLoss} onChange={(e) => setStopLoss(+e.target.value)} />

        <label>期間（年）</label>
        <input type="number" min={1} max={10} value={years} onChange={(e) => setYears(+e.target.value)} />

        <label>初期資金（円）</label>
        <input type="number" step={100000} value={capital} onChange={(e) => setCapital(+e.target.value)} />

        <button className="primary" onClick={run} disabled={loading}>
          {loading ? "実行中..." : "▶ バックテスト実行"}
        </button>
      </aside>

      <section>
        {error && <div className="error">{error}</div>}

        {!results.length && !loading && (
          <div className="panel">
            <p>左で銘柄と条件を選んで実行。グラフはズーム・パン可能（Plotly）。</p>
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>
              ※ パラメータ探索（1000通り）は Vercel の制限で非対応。Streamlit 版をローカルで使用してください。
              <br />
              ※ 株価は Yahoo Finance 経由。連続実行で制限される場合は1分待って再試行。
            </p>
          </div>
        )}

        {results.map((r) => {
          const name = ALL_TICKERS[r.ticker] ?? r.ticker;
          return (
            <div key={r.ticker} className="panel" style={{ marginBottom: 20 }}>
              <h2>
                {name} ({r.ticker})
              </h2>
              <div className="metrics">
                <div className="metric">
                  <div className="label">リターン</div>
                  <div className="value">{r.totalReturnPct.toFixed(1)}%</div>
                </div>
                <div className="metric">
                  <div className="label">B&H</div>
                  <div className="value">{r.buyHoldReturnPct.toFixed(1)}%</div>
                </div>
                <div className="metric">
                  <div className="label">勝率</div>
                  <div className="value">{r.winRatePct.toFixed(1)}%</div>
                </div>
                <div className="metric">
                  <div className="label">最大DD</div>
                  <div className="value">{r.maxDrawdownPct.toFixed(1)}%</div>
                </div>
              </div>

              <EquityChart result={r} />

              <button className="primary" style={{ width: "auto", marginTop: 12 }} onClick={() => downloadCsv(r)}>
                CSV ダウンロード
              </button>

              <details style={{ marginTop: 12 }}>
                <summary>トレード一覧 ({r.numTrades})</summary>
                <table>
                  <thead>
                    <tr>
                      <th>買い</th>
                      <th>売り</th>
                      <th>損益%</th>
                      <th>理由</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.trades.map((t, i) => (
                      <tr key={i}>
                        <td>{t.entryDate}</td>
                        <td>{t.exitDate}</td>
                        <td>{t.pnlPct.toFixed(2)}%</td>
                        <td>{t.exitReason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </div>
          );
        })}
      </section>
    </div>
  );
}
