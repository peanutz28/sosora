import type { AppState, Assessment, BridgeCandidate, CalculatedRoute, OpsEvent } from "@/lib/types";

export const eventKey = (event: OpsEvent) =>
  `${event.id}-${event.kind}-${event.at}`;
export function mergeEvents(...groups: OpsEvent[][]): OpsEvent[] {
  const unique = new Map<string, OpsEvent>();
  for (const event of groups.flat()) unique.set(eventKey(event), event);
  return [...unique.values()]
    .sort((a, b) => a.at.localeCompare(b.at) || a.id - b.id)
    .slice(-240);
}
/** A reset snapshot replaces events from the previous take, including streamed results. */
export function reconcileEvents(previous: OpsEvent[], snapshot: OpsEvent[], reset: boolean): OpsEvent[] {
  return reset ? mergeEvents(snapshot) : mergeEvents(previous, snapshot);
}
export function latestAssessment(stream: OpsEvent[]): Assessment | null {
  const event = [...stream]
    .reverse()
    .find(
      (e) =>
        e.kind === "agent_tool_result" &&
        e.tool === "submit_assessment" &&
        !e.result?.error,
    );
  const result = event?.result;
  if (!result || typeof result.summary !== "string") return null;
  return {
    summary: result.summary,
    affected_incident_ids: Array.isArray(result.affected_incident_ids)
      ? result.affected_incident_ids.filter(
          (id): id is string => typeof id === "string",
        )
      : [],
    needs_human_review: result.needs_human_review === true,
  };
}
export function reviewCandidates(
  stream: OpsEvent[],
  assessment: Assessment | null,
): BridgeCandidate[] {
  if (!assessment?.needs_human_review) return [];
  const event = [...stream]
    .reverse()
    .find((e) => e.kind === "agent_tool_result" && e.tool === "find_segments");
  if (
    Number(event?.result?.distinct_locations) <= 1 ||
    !Array.isArray(event?.result?.candidates)
  )
    return [];
  const groups = new Map<string, BridgeCandidate>();
  // Only show the equally plausible matches that produced the ambiguity, not all fuzzy matches.
  const rows = event.result.candidates as Array<{
    id?: string;
    name?: string;
    centroid?: unknown;
    match_score?: number;
  }>;
  const best = Number(rows[0]?.match_score ?? 0);
  for (const row of rows) {
    if (
      !row.id ||
      Number(row.match_score ?? 0) < best * 0.85 ||
      !Array.isArray(row.centroid) ||
      row.centroid.length !== 2 ||
      !row.centroid.every(Number.isFinite)
    )
      continue;
    const id = row.id.replace(/:(f|b)$/, "");
    if (!groups.has(id))
      groups.set(id, {
        id,
        name: row.name || "Bridge",
        centroid: row.centroid as [number, number],
        label: String.fromCharCode(65 + groups.size),
      });
  }
  return [...groups.values()]
    .sort((a, b) => b.centroid[0] - a.centroid[0])
    .map((candidate, index) => ({
      ...candidate,
      label: String.fromCharCode(65 + index),
    }));
}
export function traceSummary(event: OpsEvent): string {
  if (event.kind === "agent_error")
    return event.error || "Agent unavailable; review required";
  if (event.kind === "agent_tool_call")
    return JSON.stringify(event.arguments ?? {});
  const result = event.result ?? {};
  if (result.error) return JSON.stringify(result.error);
  if (event.tool === "find_segments")
    return `${result.distinct_locations ?? 0} ${Number(result.distinct_locations) === 1 ? "bridge found" : "locations match → needs review"}`;
  if (event.tool === "recompute_reachability")
    return `${Array.isArray(result.newly_unreachable_incident_ids) ? result.newly_unreachable_incident_ids.length : 0} incidents lost access`;
  if (event.tool === "report_segment")
    return (
      [
        ...new Set(
          Object.values(result)
            .map((value) =>
              value && typeof value === "object"
                ? (value as { status?: string }).status
                : null,
            )
            .filter(Boolean),
        ),
      ].join(" · ") || "Report recorded"
    );
  if (event.tool === "get_imagery_evidence")
    return Array.isArray(event.result) && event.result.length
      ? `${event.result.length} evidence records`
      : "No associated imagery; uncertainty retained";
  if (event.tool === "get_segment_status")
    return `${Object.keys(result).length} road directions checked`;
  if (event.tool === "submit_assessment")
    return typeof result.summary === "string"
      ? result.summary
      : "Assessment recorded";
  return JSON.stringify(result);
}

/** Opposite directions on one OSM segment are one physical closure. */
export function physicalClosureCount(closures: { id: string }[]): number {
  return new Set(closures.map((closure) => closure.id.replace(/:(f|b)$/, "")))
    .size;
}

/** Only structured location ambiguity or an unresolved contested road is yellow. */
export function needsReview(stream: OpsEvent[]): boolean {
  const boundary = stream.findLastIndex(e => e.kind === "radio_received" || e.kind === "radio_location_confirmed" || (e.kind === "sensor_reading" && e.over_threshold));
  const current = stream.slice(Math.max(0, boundary));
  const found = [...current].reverse().find(e => e.kind === "agent_tool_result" && e.tool === "find_segments" && !e.result?.error);
  if (found && (found.result?.needs_human_review === true || Number(found.result?.distinct_locations) > 1)) return true;
  const statuses = new Map<string, string>();
  for (const event of stream) {
    if (event.kind !== "agent_tool_result" || !["report_segment", "get_segment_status"].includes(event.tool || "")) continue;
    for (const [id, value] of Object.entries(event.result || {})) {
      if (value && typeof value === "object" && "status" in value) statuses.set(id, String(value.status));
    }
  }
  return [...statuses.values()].includes("contested");
}

export function agentStatus(
  working: boolean,
  assessment: Assessment | null,
  stream: OpsEvent[] = [],
): "idle" | "working" | "needs review" | "ready for operator" | "action required" {
  if (working) return "working";
  if (needsReview(stream)) return "needs review";
  const submitted = [...stream].reverse().find(e => e.kind === "agent_tool_result" && e.tool === "submit_assessment");
  const boundary = stream.findLastIndex(e => e.kind === "radio_received" || e.kind === "radio_location_confirmed" || (e.kind === "sensor_reading" && e.over_threshold));
  const found = stream.slice(Math.max(0, boundary)).findLast(e => e.kind === "agent_tool_result" && e.tool === "find_segments");
  if (submitted?.call_id === "fallback" || submitted?.result?.error || found?.result?.distinct_locations === 0) return "action required";
  return assessment ? "ready for operator" : "idle";
}

export const agentStatusLabel = (status: ReturnType<typeof agentStatus>) => status[0].toUpperCase() + status.slice(1);

/** Publish all three counters from the same completed reachability snapshot. */
export function accessCounters(state: AppState, stream: OpsEvent[]) {
  const index = stream.findLastIndex(e => e.kind === "agent_tool_result" && e.tool === "recompute_reachability" && e.result?.routes && !e.result.error);
  const routes = index >= 0 ? stream[index].result?.routes as Record<string, CalculatedRoute> : null;
  let cutOff = 0, reachable = 0;
  for (const incident of state.incidents) {
    const route = routes?.[incident.id];
    if (route ? route.status === "ok" : incident.reachable === true) reachable++;
    if (route ? route.status === "unreachable" : incident.reachable === false && incident.route?.status !== "snap_failed") cutOff++;
  }
  const blocked = new Set(state.closures.map(c => c.id.replace(/:(f|b)$/, "")));
  for (const event of stream.slice(0, index + 1)) {
    if (event.kind !== "agent_tool_result" || !["report_segment", "get_segment_status"].includes(event.tool || "")) continue;
    for (const [id, value] of Object.entries(event.result || {})) {
      if (!value || typeof value !== "object" || !("status" in value)) continue;
      const physical = id.replace(/:(f|b)$/, "");
      if (value.status === "blocked" || value.status === "contested") blocked.add(physical);
      else if (value.status === "open_official") blocked.delete(physical);
    }
  }
  return { cutOff, reachable, blocked: blocked.size };
}

export function agentTraceBadge(stream: OpsEvent[], demoMode: boolean) {
  const runtime = [...stream].reverse().find(e => e.agent_runtime)?.agent_runtime;
  if (process.env.NEXT_PUBLIC_HOSTED_DEMO === "true" || demoMode || runtime?.cached) return { label: "cached replay", title: "Cached tool replay; no live model call or latency" };
  if (!runtime?.model_id) return { label: "Model metadata unavailable", title: "No successful model-call metadata has arrived" };
  const model = /nemotron[-_ ]3\.5[-_ ]lightning/i.test(runtime.model_id) ? "Nemotron 3.5 Lightning" : runtime.model_id;
  const latency = runtime.last_call_latency_ms;
  const timing = typeof latency === "number" && Number.isFinite(latency) && latency >= 0 ? `${(latency / 1000).toFixed(2)}s` : "latency unavailable";
  return { label: `${model} · ${runtime.serving_backend || "serving unknown"} · ${timing}`, title: `Model: ${runtime.model_id}. Last successful model HTTP call; excludes routing and tool execution.` };
}
