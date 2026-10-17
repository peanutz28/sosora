"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE, api, fetchRoads, readState } from "@/lib/api";
import type { AppState, FeatureCollection } from "@/lib/types";

type IncidentBody = {
  client_id: string;
  source_id: string;
  lon: number;
  lat: number;
  message: string;
  people_affected?: number;
  medical?: string;
  mobility?: string;
};

export function useOps() {
  const [state, setState] = useState<AppState | null>(null);
  const [roads, setRoads] = useState<FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [roadsError, setRoadsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [socketLive, setSocketLive] = useState(false);

  const apply = useCallback((next: AppState) => {
    setState((prev) => {
      if (!prev || next.revision > prev.revision) return next;
      return prev;
    });
  }, []);

  const refresh = useCallback(async () => {
    const next = await api<AppState>("/api/state");
    apply(next);
    setError(null);
  }, [apply]);

  useEffect(() => {
    let stop = false;
    api<AppState>("/api/state")
      .then((next) => {
        if (!stop) apply(next);
      })
      .catch(() => {
        if (!stop) setError("Routing service is not responding.");
      });
    fetchRoads()
      .then((next) => {
        if (!stop) setRoads(next);
      })
      .catch(() => {
        if (!stop) setRoadsError("Road graph overlay did not load. The basemap is still available.");
      });
    const poll = window.setInterval(() => {
      refresh().catch(() => setError("Routing service is not responding."));
    }, 5000);
    const socket = new WebSocket(`${API_BASE.replace(/^http/, "ws")}/ws/events`);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { state?: AppState };
        if (payload.state) apply(payload.state);
      } catch {
        /* ignore malformed event frames */
      }
    };
    socket.onopen = () => {
      setSocketLive(true);
      setError(null);
    };
    socket.onclose = () => setSocketLive(false);
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
        const next = await api<AppState | { state: AppState }>(path, {
          method: "POST",
          body: body === undefined ? undefined : JSON.stringify(body),
        });
        const resolved = readState(next);
        apply(resolved);
        setError(null);
        return next;
      } catch {
        setError("The last action did not reach the routing service.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [apply],
  );

  const advance = useCallback(() => mutate("/api/scenarios/advance"), [mutate]);
  const reset = useCallback(() => mutate("/api/scenarios/reset"), [mutate]);
  const goto = useCallback((step: number) => mutate("/api/scenarios/goto", { step }), [mutate]);
  const acknowledge = useCallback(() => mutate("/api/review", { decision: "acknowledged" }), [mutate]);
  const createIncident = useCallback((body: IncidentBody) => mutate("/api/incidents", body), [mutate]);

  return {
    state,
    roads,
    error,
    roadsError,
    busy,
    socketLive,
    advance,
    reset,
    goto,
    acknowledge,
    createIncident,
    refresh,
  };
}
