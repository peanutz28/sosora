"use client";

import { useCallback, useEffect, useState } from "react";
import type { AppState, FeatureCollection } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_APP_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
}

export function useOps() {
  const [state, setState] = useState<AppState | null>(null);
  const [roads, setRoads] = useState<FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((next: AppState) => {
    setState((prev) => {
      if (!prev || next.revision >= prev.revision) return next;
      return prev;
    });
  }, []);

  const refresh = useCallback(async () => {
    const next = await request<AppState>("/api/state");
    apply(next);
    setError(null);
  }, [apply]);

  useEffect(() => {
    let stop = false;
    request<AppState>("/api/state")
      .then((next) => {
        if (!stop) apply(next);
      })
      .catch(() => {
        if (!stop) setError("Routing service is not responding.");
      });
    request<FeatureCollection>("/api/roads")
      .then((next) => {
        if (!stop) setRoads(next);
      })
      .catch(() => {
        if (!stop) setError("Road layer did not load.");
      });
    const poll = window.setInterval(() => {
      refresh().catch(() => setError("Routing service is not responding."));
    }, 4000);
    const socket = new WebSocket(BASE.replace(/^http/, "ws") + "/ws/events");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.state) apply(payload.state);
    };
    socket.onopen = () => setError(null);
    return () => {
      stop = true;
      window.clearInterval(poll);
      socket.close();
    };
  }, [apply, refresh]);

  const mutate = useCallback(
    async (path: string, body?: unknown) => {
      setBusy(true);
      try {
        const next = await request<AppState | { state: AppState }>(path, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        });
        apply("state" in next ? next.state : next);
        setError(null);
      } catch {
        setError("The last action did not reach the routing service.");
      } finally {
        setBusy(false);
      }
    },
    [apply],
  );

  const advance = useCallback(() => mutate("/api/scenarios/advance"), [mutate]);
  const reset = useCallback(() => mutate("/api/scenarios/reset"), [mutate]);
  const acknowledge = useCallback(() => mutate("/api/review", { decision: "acknowledged" }), [mutate]);
  const injectSos = useCallback(() => {
    if (!state) return;
    return mutate("/api/incidents", {
      client_id: "sos-swannanoa-demo-01",
      source_id: "demo-handset-04",
      lon: state.objective.lon,
      lat: state.objective.lat,
      message:
        "Water is at the doors. Two adults and a child are inside. One adult cannot walk out. The road toward the highway is underwater.",
      people_affected: 3,
      medical: "Child has asthma. Inhaler is nearly empty.",
      mobility: "One adult needs assistance to move.",
    });
  }, [mutate, state]);

  return { state, roads, error, busy, advance, reset, acknowledge, injectSos, refresh };
}
