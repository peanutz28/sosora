import type { AppState, CalculatedRoute, FeatureCollection } from "@/lib/types";

export const API_BASE = process.env.NEXT_PUBLIC_APP_API_URL ?? "http://127.0.0.1:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${path}`);
  }
  return response.json() as Promise<T>;
}

export function readState(payload: AppState | { state: AppState }): AppState {
  return "scenario" in payload ? payload : payload.state;
}

export async function fetchRoads(): Promise<FeatureCollection> {
  return api<FeatureCollection>("/api/roads");
}

export async function calculateRoute(origin: [number, number], destination: [number, number]): Promise<CalculatedRoute> {
  const payload = await api<{ route: CalculatedRoute }>("/api/routes/calculate", {
    method: "POST",
    body: JSON.stringify({ origin, destination }),
  });
  return payload.route;
}
