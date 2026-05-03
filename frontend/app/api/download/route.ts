import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const cases = searchParams.get("cases_per_topic") ?? "20";
    const res = await fetch(
      `${BACKEND}/api/ingest/download?cases_per_topic=${cases}`,
      { method: "POST" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
