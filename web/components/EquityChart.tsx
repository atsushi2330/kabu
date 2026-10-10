"use client";

import dynamic from "next/dynamic";
import type { BacktestResult } from "@/lib/types";
import { ALL_TICKERS } from "@/lib/presets";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  result: BacktestResult;
}

export default function EquityChart({ result }: Props) {
  const name = ALL_TICKERS[result.ticker] ?? result.ticker;
  const capital = result.params.initialCapital;
  const eqMap = new Map(result.equityCurve.map((p) => [p.date, p.equity]));
  const prices = result.prices.slice(1);

  const eqX = prices.map((p) => p.date);
  const eqY = prices.map((p) => eqMap.get(p.date) ?? capital);
  const bhY = prices.map((p) => (p.close / prices[0].close) * capital);
  const pxY = prices.map((p) => p.close);

  const ddY = eqY.map((v, i) => {
    const peak = Math.max(...eqY.slice(0, i + 1));
    return ((v - peak) / peak) * 100;
  });

  const winEntry = result.trades.filter((t) => t.pnl > 0);
  const lossEntry = result.trades.filter((t) => t.pnl <= 0);

  const p = result.params;

  return (
    <Plot
      data={[
        { x: eqX, y: eqY, name: "資産", type: "scatter", line: { color: "#2563eb", width: 2 } },
        { x: eqX, y: bhY, name: "B&H", type: "scatter", line: { color: "#9ca3af", width: 1.5, dash: "dot" } },
        {
          x: eqX,
          y: pxY,
          name: "株価",
          type: "scatter",
          yaxis: "y2",
          line: { color: "#7c3aed", width: 1.2 },
          opacity: 0.7,
        },
        {
          x: winEntry.map((t) => t.entryDate),
          y: winEntry.map((t) => eqMap.get(t.entryDate) ?? capital),
          name: "▲ 買い（勝ち）",
          mode: "markers",
          marker: { symbol: "triangle-up", size: 9, color: "#16a34a" },
        },
        {
          x: winEntry.map((t) => t.exitDate),
          y: winEntry.map((t) => eqMap.get(t.exitDate) ?? capital),
          name: "▼ 売り（勝ち）",
          mode: "markers",
          marker: { symbol: "triangle-down", size: 9, color: "#16a34a" },
        },
        {
          x: lossEntry.map((t) => t.entryDate),
          y: lossEntry.map((t) => eqMap.get(t.entryDate) ?? capital),
          name: "▲ 買い（負け）",
          mode: "markers",
          marker: { symbol: "triangle-up", size: 9, color: "#dc2626" },
        },
        {
          x: lossEntry.map((t) => t.exitDate),
          y: lossEntry.map((t) => eqMap.get(t.exitDate) ?? capital),
          name: "▼ 売り（負け）",
          mode: "markers",
          marker: { symbol: "triangle-down", size: 9, color: "#dc2626" },
        },
        {
          x: eqX,
          y: ddY,
          name: "DD",
          type: "scatter",
          xaxis: "x2",
          yaxis: "y3",
          fill: "tozeroy",
          line: { color: "#dc2626", width: 1 },
        },
      ]}
      layout={{
        title: `${name} — -${p.entryDropPct}% / +${p.takeProfitPct}% / -${p.stopLossPct}% | ${result.totalReturnPct.toFixed(1)}%`,
        height: 680,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis: { domain: [0, 1], anchor: "y" },
        yaxis: { title: "資産 (円)", domain: [0.35, 1] },
        yaxis2: { title: "株価 (円)", overlaying: "y", side: "right", showgrid: false },
        xaxis2: { domain: [0, 1], anchor: "y3", matches: "x" },
        yaxis3: { title: "DD (%)", domain: [0, 0.28] },
        legend: { orientation: "h", y: 1.08 },
        margin: { t: 60, r: 60, b: 40, l: 60 },
        hovermode: "x unified",
      }}
      config={{ responsive: true, displayModeBar: true }}
      style={{ width: "100%" }}
    />
  );
}
