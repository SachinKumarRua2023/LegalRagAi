import type { QueryResponse, IndexedFile, IndexStatus } from "./types";

const BASE = "";

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function getStoredUser(): { username: string; role: string } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("auth_user");
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}

export function logout() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
  window.location.href = "/login";
}

export async function loginUser(username: string, password: string) {
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  let data: Record<string, string> = {};
  try { data = await res.json(); } catch { /* HTML response — backend not ready */ }
  if (res.status === 404 || res.status === 503) {
    throw new Error("Backend is still starting up — wait 30 seconds and try again.");
  }
  if (!res.ok) throw new Error(data.detail || data.error || "Invalid username or password");
  localStorage.setItem("auth_token", data.token);
  localStorage.setItem("auth_user", JSON.stringify({ username: data.username, role: data.role }));
  return data;
}

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuthHeader(), ...init?.headers },
    ...init,
  });
  if (res.status === 401) {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const json = await res.json();
      msg = json.error || json.detail || json.message || res.statusText;
    } catch {}
    throw new Error(msg);
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
  const data = await apiFetch("/api/files");
  return Array.isArray(data) ? data : [];
}

export async function getStatus(): Promise<IndexStatus> {
  return apiFetch("/api/status");
}

export async function uploadFile(file: File): Promise<{ status: string; file: string; result: { chunks_added?: number } }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", headers: getAuthHeader(), body: form });
  if (res.status === 401) { logout(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function triggerDownload(casesPerTopic = 20) {
  return apiFetch(`/api/download?cases_per_topic=${casesPerTopic}`, { method: "POST" });
}
