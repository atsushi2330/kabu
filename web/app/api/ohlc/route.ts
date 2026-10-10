import { NextRequest, NextResponse } from "next/server";
import yahooFinance from "yahoo-finance2";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function GET(req: NextRequest) {
  const ticker = req.nextUrl.searchParams.get("ticker");
  const years = Number(req.nextUrl.searchParams.get("years") ?? "5");

  if (!ticker) {
    return NextResponse.json({ error: "ticker required" }, { status: 400 });
  }

  try {
    const end = new Date();
    const start = new Date();
    start.setFullYear(start.getFullYear() - years);

    const raw = await yahooFinance.historical(ticker, {
      period1: start,
      period2: end,
      interval: "1d",
    });

    const bars = raw
      .filter((r) => r.open != null && r.high != null && r.low != null && r.close != null)
      .map((r) => ({
        date: r.date.toISOString().slice(0, 10),
        open: r.open!,
        high: r.high!,
        low: r.low!,
        close: r.close!,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (bars.length < 60) {
      return NextResponse.json({ error: "insufficient data" }, { status: 422 });
    }

    return NextResponse.json({ ticker, bars });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
