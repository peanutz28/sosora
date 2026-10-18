"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, api, fetchRoads, readState } from "@/lib/api";
import { mergeEvents } from "@/lib/ops";
import type {
  AppState,
  Beacon,
  BridgeCandidate,
  DrillSeed,
  FeatureCollection,
  OpsEvent,
} from "@/lib/types";

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
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [roadsError, setRoadsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [socketLive, setSocketLive] = useState(false);
  const [stream, setStream] = useState<OpsEvent[]>([]);
  const [agentWorking, setAgentWorking] = useState(false);
  const [seed, setSeed] = useState<DrillSeed | null>(null);
  const [flyToken, setFlyToken] = useState(0);
  const assessmentComplete = useRef(false);
  const inFlight = useRef(false);
  const seedEpoch = useRef(0);
  const revision = useRef(-1);
  const seedRef = useRef<DrillSeed | null>(null);

  const apply = useCallback((next: AppState) => {
    if (next.revision < revision.current) return;
    revision.current = next.revision;
    setState((prev) => (!prev || next.revision > prev.revision ? next : prev));
    setStream((prev) => mergeEvents(prev, next.events as OpsEvent[]));
  }, []);
  const refresh = useCallback(async () => {
    apply(await api<AppState>("/api/state"));
    setError(null);
  }, [apply]);
  useEffect(() => {
    let stop = false;
    api<AppState>("/api/state")
      .then((next) => {
        if (!stop) apply(next);
      })
      .catch(() => {
        if (!stop)
          setError("Command is not responding. Check the local backend.");
      });
    fetchRoads()
      .then((next) => {
        if (!stop) setRoads(next);
      })
      .catch(() => {
        if (!stop)
          setRoadsError(
            "Road overlay unavailable; operational closures remain visible.",
          );
      });
    api<{ beacons: Beacon[] }>("/api/beacons")
      .then((next) => {
        if (!stop) setBeacons(next.beacons);
      })
      .catch(() => {
        if (!stop)
          setRoadsError(
            "Beacon registry unavailable; no beacon positions inferred.",
          );
      });
    const poll = window.setInterval(() => {
      if (!inFlight.current) void refresh().catch(() => {});
    }, 5000);
    let socket: WebSocket;
    let reconnect: ReturnType<typeof setTimeout>;
    const connect = () => {
      socket = new WebSocket(`${API_BASE.replace(/^http/, "ws")}/ws/events`);
      socket.onmessage = (message) => {
        try {
          const payload = JSON.parse(message.data) as {
            type?: string;
            state?: AppState;
            event?: OpsEvent;
          };
          if (
            payload.event &&
            (payload.type === "agent_event" || payload.type === "radio_event")
          ) {
            const event = payload.event;
            setStream((prev) => mergeEvents(prev, [event]));
            if (
              event.kind === "radio_received" ||
              (event.kind === "sensor_reading" && event.over_threshold) ||
              event.kind === "radio_location_confirmed"
            ) {
              assessmentComplete.current = false;
              setAgentWorking(true);
            }
            if (
              event.kind === "agent_tool_result" &&
              event.tool === "submit_assessment"
            )
              assessmentComplete.current = true;
          }
          if (payload.state) {
            apply(payload.state);
            if (assessmentComplete.current) {
              setAgentWorking(false);
              assessmentComplete.current = false;
            }
          }
        } catch {
          /* malformed frames cannot alter state */
        }
      };
      socket.onopen = () => {
        setSocketLive(true);
        setError(null);
      };
      socket.onclose = () => {
        setSocketLive(false);
        if (!stop) reconnect = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      stop = true;
      clearInterval(poll);
      clearTimeout(reconnect);
      socket?.close();
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
        apply(readState(next));
        setError(null);
        return next;
      } catch {
        setError("The last action did not reach Command.");
        return null;
      } finally {
        setBusy(false);
      }
    },
    [apply],
  );
  const clear = useCallback(() => {
    seedEpoch.current += 1;
    setStream([]);
    setAgentWorking(false);
    assessmentComplete.current = false;
  }, []);
  const reset = useCallback(async () => {
    if (inFlight.current) return;
    clear();
    setSeed(null);
    return mutate("/api/scenarios/reset");
  }, [clear, mutate]);
  const seedDrill = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    clear();
    setBusy(true);
    try {
      const next = await api<DrillSeed>("/api/radio/demo/seed", {
        method: "POST",
      });
      setSeed(next);
      seedRef.current = next;
      setStream(next.state.events as OpsEvent[]);
      apply(next.state);
      setFlyToken((value) => value + 1);
      setError(null);
      return next;
    } catch {
      setError("Could not seed the drill. Check Command and try again.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [apply, clear]);
  const radioAction = useCallback(
    async (
      action: "beacon" | "responder" | "dot" | "water",
      candidate?: BridgeCandidate,
      radioId?: string,
    ) => {
      const currentSeed = seedRef.current;
      if (inFlight.current || (!currentSeed && !candidate)) return;
      inFlight.current = true;
      setAgentWorking(true);
      setError(null);
      assessmentComplete.current = false;
      const epoch = seedEpoch.current;
      let path = "/api/radio";
      let body: unknown;
      if (candidate && radioId) {
        path = "/api/radio/confirm";
        body = {
          radio_id: radioId,
          lon: candidate.centroid[0],
          lat: candidate.centroid[1],
        };
      } else if (action === "water") {
        path = "/api/beacon/beacon-ww-bridge/reading";
        body = { water_level_cm: 45 };
      } else if (currentSeed)
        body =
          action === "beacon"
            ? {
                message: currentSeed.hero_message,
                source_type: "beacon",
                ...currentSeed.beacon_position,
              }
            : {
                message:
                  action === "dot"
                    ? currentSeed.open_report
                    : currentSeed.hero_message,
                unit: action === "dot" ? "DOT" : "Engine 4",
                source_type: "responder_radio",
              };
      try {
        const result = await api<{ state: AppState }>(path, {
          method: "POST",
          body: JSON.stringify(body),
        });
        if (epoch === seedEpoch.current) apply(result.state);
      } catch {
        if (epoch === seedEpoch.current)
          setError("Report outcome unknown. Check the trace before retrying.");
      } finally {
        inFlight.current = false;
        if (epoch === seedEpoch.current) setAgentWorking(false);
      }
    },
    [seed, apply],
  );
  return {
    state,
    roads,
    beacons,
    error,
    roadsError,
    busy,
    socketLive,
    stream,
    agentWorking,
    seed,
    flyToken,
    seedDrill,
    radioAction,
    reset,
    goto: useCallback(
      (step: number) => mutate("/api/scenarios/goto", { step }),
      [mutate],
    ),
    acknowledge: useCallback(
      () => mutate("/api/review", { decision: "acknowledged" }),
      [mutate],
    ),
    createIncident: useCallback(
      (body: IncidentBody) => mutate("/api/incidents", body),
      [mutate],
    ),
    refresh,
  };
}
