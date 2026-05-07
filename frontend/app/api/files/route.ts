import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/api/files`, { cache: "no-store" });
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      return NextResponse.json([], { status: 503 });
    }
    const data = await res.json();
    // Guard: backend error objects must not leak to the client as "data"
    return NextResponse.json(Array.isArray(data) ? data : [], { status: res.status });
  } catch {
    return NextResponse.json([], { status: 503 });
  }
}
