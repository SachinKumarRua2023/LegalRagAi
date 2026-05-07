import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const auth = req.headers.get("authorization") || "";
    const res = await fetch(`${BACKEND}/api/upload`, {
      method: "POST",
      headers: auth ? { Authorization: auth } : {},
      body: form,
    });
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      return NextResponse.json({ error: "Backend warming up, please retry in 30 seconds." }, { status: 503 });
    }
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
