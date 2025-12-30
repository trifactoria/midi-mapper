// components/useMidiApi.ts
export const API_BASE = "http://127.0.0.1:8765";

async function parseJsonSafe(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const body = await parseJsonSafe(res);
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText} :: ${JSON.stringify(body)}`);
  }
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const payload = await parseJsonSafe(res);
    throw new Error(`POST ${path} failed: ${res.status} ${res.statusText} :: ${JSON.stringify(payload)}`);
  }

  const data = await parseJsonSafe(res);
  return data as T;
}
