import type { Assessment, BridgeCandidate, OpsEvent } from "@/lib/types";

export const eventKey = (event: OpsEvent) =>
  `${event.id}-${event.kind}-${event.at}`;
export function mergeEvents(...groups: OpsEvent[][]): OpsEvent[] {
  const unique = new Map<string, OpsEvent>();
  for (const event of groups.flat()) unique.set(eventKey(event), event);
  return [...unique.values()]
    .sort((a, b) => a.at.localeCompare(b.at) || a.id - b.id)
    .slice(-240);
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

export function agentStatus(
  working: boolean,
  assessment: Assessment | null,
): "idle" | "working" | "needs review" {
  return working
    ? "working"
    : assessment?.needs_human_review
      ? "needs review"
      : "idle";
}
