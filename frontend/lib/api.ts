import type { QueryResponse, IndexedFile, IndexStatus } from "./types";

// In the browser, calls go to Next.js API proxy routes (/api/*)
// Those routes forward to BACKEND_URL (server-side env var → safe)
const BASE = "";

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export async function sendQuery(
  question: string,
  options?: {
    top_k?: number;
    filter_file?: string;
    filter_folder?: string;
    filter_file_type?: string;
  }
): Promise<QueryResponse> {
  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ question, top_k: 5, ...options }),
  });
}

export async function listFiles(): Promise<IndexedFile[]> {
  return apiFetch("/api/files");
}

export async function getStatus(): Promise<IndexStatus> {
  return apiFetch("/api/status");
}

export async function uploadFile(file: File): Promise<{ status: string; file: string; result: { chunks_added?: number } }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function triggerDownload(casesPerTopic = 20) {
  return apiFetch(`/api/download?cases_per_topic=${casesPerTopic}`, { method: "POST" });
}
