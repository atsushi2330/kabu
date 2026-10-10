import yahooFinance from "yahoo-finance2";
import type { OhlcBar } from "./types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function isRateLimitError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  return (
    msg.includes("Too Many Requests") ||
    msg.includes("429") ||
    msg.includes("Unexpected token") ||
    msg.toLowerCase().includes("rate limit")
  );
}

function toBars(
  raw: Array<{
    date: Date;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    close?: number | null;
  }>,
): OhlcBar[] {
  return raw
    .filter((r) => r.open != null && r.high != null && r.low != null && r.close != null)
    .map((r) => ({
      date: r.date.toISOString().slice(0, 10),
      open: r.open!,
      high: r.high!,
      low: r.low!,
      close: r.close!,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

async function fetchOnce(ticker: string, start: Date, end: Date): Promise<OhlcBar[]> {
  const raw = await yahooFinance.historical(ticker, {
    period1: start,
    period2: end,
    interval: "1d",
  });
  return toBars(raw);
}

/** Yahoo Finance から OHLC 取得（リトライ付き） */
export async function fetchOhlcFromYahoo(
  ticker: string,
  years: number,
): Promise<OhlcBar[]> {
  const end = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - years);

  const retries = [0, 1500, 3000];
  let lastError: unknown;

  for (let i = 0; i < retries.length; i++) {
    if (retries[i] > 0) await sleep(retries[i]);
    try {
      const bars = await fetchOnce(ticker, start, end);
      if (bars.length < 60) {
        throw new Error(`データ不足 (${bars.length} 日): ${ticker}`);
      }
      return bars;
    } catch (e) {
      lastError = e;
      if (!isRateLimitError(e) || i === retries.length - 1) break;
    }
  }

  if (isRateLimitError(lastError)) {
    throw new Error(
      "Yahoo Finance のアクセス制限（Too Many Requests）。30秒〜1分待って再実行してください。",
    );
  }
  throw lastError instanceof Error ? lastError : new Error("株価取得に失敗しました");
}
