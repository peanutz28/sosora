"use client";

import { km, titleCase } from "@/lib/format";
import type { AppState, Incident } from "@/lib/types";

export function IntelRail({
  state,
  incident,
  onAcknowledge,
  busy,
}: {
  state: AppState;
  incident: Incident | null;
  onAcknowledge: () => void;
  busy: boolean;
}) {
  const route = state.routes.active ?? state.routes.invalidated;
  const status = state.routes.status;
  const detection = state.detections[0];

  return (
    <aside className="flex w-[340px] shrink-0 flex-col border-l border-line bg-panel">
      <div className="min-h-0 flex-1 overflow-auto">
        <Section kicker="Access" title={statusLabel(status)}>
          <Row label="Graph length" value={km(route?.length_m)} />
          <Row label="Segments" value={route ? String(route.edge_count) : "—"} />
          <Row label="Snap" value={route ? `${Math.round(route.origin_snap_m)} m / ${Math.round(route.destination_snap_m)} m` : "—"} />
          <Row label="Roads" value={route?.roads.filter((name) => name !== "Unnamed segment").slice(0, 3).join(" · ") || "—"} />
          <p className="mt-2 text-[11px] leading-snug text-muted">{accessCopy(state)}</p>
        </Section>

        <Section kicker="Evidence" title={detection ? titleCase(detection.class) : "None on this step"}>
          {detection ? (
            <>
              <Row label="Mode" value={detection.inference_mode} />
              <Row label="Confidence" value={detection.confidence == null ? "Not measured" : detection.confidence.toFixed(2)} />
              <Row label="Review" value={detection.review_status} />
              <Row label="Model" value={detection.model_version ?? "Not called"} />
              <p className="mt-2 text-[11px] leading-snug text-muted">{detection.confidence_note || detection.map_note}</p>
            </>
          ) : (
            <p className="text-[12px] leading-snug text-muted">No damage geometry is on the map for this step.</p>
          )}
          <p className="mt-2 text-[11px] leading-snug text-faint">{state.imagery.alignment_note}</p>
        </Section>

        <Section kicker="Interpretation" title={state.explanation ? modeTitle(state.explanation.inference_mode) : "Not on this step"}>
          {state.explanation ? (
            <>
              <p className="text-[12px] leading-snug">{state.explanation.summary}</p>
              {state.explanation.access ? <p className="mt-2 text-[12px] leading-snug text-info">{state.explanation.access}</p> : null}
              <ul className="mt-2 space-y-1">
                {(state.explanation.uncertainties ?? []).map((item) => (
                  <li key={item} className="text-[11px] leading-snug text-muted">
                    {item}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-[12px] leading-snug text-muted">{state.ml.detail}</p>
          )}
        </Section>

        <Section kicker="Review" title={state.review.status.replaceAll("_", " ")}>
          <p className="text-[12px] leading-snug">{state.review.note}</p>
          {incident ? (
            <p className="mt-2 text-[12px] leading-snug text-muted">
              {incident.medical} {incident.mobility}
            </p>
          ) : null}
          <button
            type="button"
            disabled={busy || state.review.status !== "requested"}
            onClick={onAcknowledge}
            className="mt-3 h-8 w-full border border-line text-[12px] disabled:opacity-40"
          >
            {state.review.status === "acknowledged" ? "Acknowledged" : "Acknowledge review"}
          </button>
        </Section>
      </div>
      <p className="border-t border-line px-3 py-2 text-[10px] leading-snug text-faint">{state.system.disclaimer}</p>
    </aside>
  );
}

function statusLabel(status: AppState["routes"]["status"]): string {
  if (status === "proposed") return "Candidate route";
  if (status === "invalidated") return "Route withdrawn";
  if (status === "rerouted") return "Replacement route";
  if (status === "unreachable") return "Potentially isolated";
  return "No candidate";
}

function accessCopy(state: AppState): string {
  if (state.routes.status === "unreachable" && state.scenario.step >= 6) {
    return "POTENTIALLY ISOLATED — No available path in the current road graph.";
  }
  if (state.routes.conflicts) return "The candidate still uses a segment the simulation has closed.";
  if (state.routes.status === "rerouted") return "The replacement was calculated from the graph after the closure. It is not a claim that the road is open in the field.";
  if (state.routes.status === "proposed") return "Shortest path on the current OpenStreetMap graph. Length is graph distance, not travel time.";
  return state.system.graph_note;
}

function modeTitle(mode: string): string {
  if (mode === "real") return "Model response";
  if (mode === "unavailable") return "Model unavailable";
  return "Local template";
}

function Section({ kicker, title, children }: { kicker: string; title: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line px-3 py-3">
      <p className="text-[10px] tracking-[0.16em] text-faint uppercase">{kicker}</p>
      <h2 className="mt-1 text-[13px] font-medium capitalize">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5">
      <span className="text-[11px] text-muted">{label}</span>
      <span className="mono truncate text-right text-[11px]">{value}</span>
    </div>
  );
}
