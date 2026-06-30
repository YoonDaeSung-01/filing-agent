import type { AskRequest, AskResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function ask(req: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`API 오류: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<AskResponse>;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
