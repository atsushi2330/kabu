import { unstable_cache } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { fetchOhlcFromYahoo } from "@/lib/yahoo";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function GET(req: NextRequest) {
  const ticker = req.nextUrl.searchParams.get("ticker");
  const years = Number(req.nextUrl.searchParams.get("years") ?? "5");

  if (!ticker) {
    return NextResponse.json({ error: "ticker required" }, { status: 400 });
  }

  if (!Number.isFinite(years) || years < 1 || years > 10) {
    return NextResponse.json({ error: "years must be 1-10" }, { status: 400 });
  }

  const getCachedOhlc = unstable_cache(
    async () => fetchOhlcFromYahoo(ticker, years),
    ["ohlc", ticker, String(years)],
    { revalidate: 3600 },
  );

  try {
    const bars = await getCachedOhlc();
    return NextResponse.json(
      { ticker, bars },
      {
        headers: {
          "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
        },
      },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : "fetch failed";
    const status = msg.includes("Too Many Requests") || msg.includes("アクセス制限") ? 429 : 500;
    return NextResponse.json({ error: msg }, { status });
  }
}
