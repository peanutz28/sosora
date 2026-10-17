"use client";

import { useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { closureKind, km, peopleLabel, titleCase } from "@/lib/format";
import type { AppState, CalculatedRoute, QueueIncident } from "@/lib/types";

export function IntelPanel({
  state,
  incident,
  route,
  routeError,
  busy,
  onClose,
  onAcknowledge,
  onShowImagery,
}: {
  state: AppState;
  incident: QueueIncident | null;
  route: CalculatedRoute | null;
  routeError: string | null;
  busy: boolean;
  onClose: () => void;
  onAcknowledge: () => void;
  onShowImagery: (which: "before" | "after") => void;
}) {
  const detection = state.detections[0];
  const scenarioRoute = state.routes.active ?? state.routes.invalidated;
  const showExplanation = Boolean(state.explanation) && (!incident || incident.source === "backend");

  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-l border-line bg-surface">
      <div className="flex h-11 shrink-0 items-center justify-between px-3">
        <h2 className="text-[14px] font-medium">Intelligence</h2>
        <button type="button" aria-label="Close intelligence" onClick={onClose} className="grid h-7 w-7 place-items-center text-muted hover:text-ink">
          <X size={15} />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <Disclosure title="Incident overview" defaultOpen>
          {incident ? (
            <div className="space-y-1.5 text-[13px] leading-5">
              <p className="text-ink">{incident.title}</p>
              <p className="text-muted">{incident.location}</p>
              {incident.locationNote ? <p className="text-[12px] leading-5 text-faint">{incident.locationNote}</p> : null}
              <p className="text-muted">{peopleLabel(incident.people_affected)}</p>
              {incident.medical ? <p className="text-muted">{incident.medical}</p> : null}
              {incident.mobility ? <p className="text-muted">{incident.mobility}</p> : null}
              <p className="text-[12px] text-faint">
                {incident.provenance} · {incident.delivery_status} · {incident.verification}
              </p>
              {incident.map_note ? <p className="text-[12px] leading-5 text-warning">{incident.map_note}</p> : null}
            </div>
          ) : (
            <p className="text-[13px] leading-5 text-muted">Select an incident to inspect it. The corridor scenario stays on the map.</p>
          )}
        </Disclosure>

        <Disclosure title="Rescue access" defaultOpen>
          <p className="text-[13px] leading-5 text-ink">{accessHeadline(state.routes.status)}</p>
          <p className="mt-1 text-[12px] leading-5 text-muted">{accessDetail(state)}</p>
          {scenarioRoute ? (
            <p className="mt-2 text-[12px] leading-5 text-faint">
              Corridor graph length {km(scenarioRoute.length_m)} across {scenarioRoute.edge_count} segments. Not a travel time.
            </p>
          ) : null}
        </Disclosure>

        <Disclosure title="Candidate route">
          {routeError ? <p className="text-[13px] leading-5 text-warning">{routeError}</p> : null}
          {!incident ? <p className="text-[13px] leading-5 text-muted">Select an incident to calculate access from Rescue 4.</p> : null}
          {incident && !incident.map_ready ? (
            <p className="text-[13px] leading-5 text-muted">No route is calculated because this report is not on the loaded road graph.</p>
          ) : null}
          {route ? (
            <div className="space-y-1 text-[13px] leading-5">
              <p className="text-ink">{routeHeadline(route.status)}</p>
              <Row label="Graph length" value={km(route.length_m)} />
              <Row label="Segments" value={route.edge_count ? String(route.edge_count) : "—"} />
              <Row label="Snap" value={`${Math.round(route.origin_snap_m)} m / ${Math.round(route.destination_snap_m)} m`} />
              <p className="text-[12px] leading-5 text-muted">
                {route.roads.filter((name) => name && name !== "Unnamed segment").slice(0, 4).join(" · ") || "Unnamed segments"}
              </p>
              <p className="text-[12px] leading-5 text-faint">A path in the graph is not a statement that the road is safe.</p>
            </div>
          ) : null}
        </Disclosure>

        <Disclosure title="Road damage evidence">
          {state.closures.length === 0 && !detection ? (
            <p className="text-[13px] leading-5 text-muted">No closure or damage geometry is active on this stage.</p>
          ) : null}
          {state.closures[0] ? (
            <div className="text-[13px] leading-5">
              <p className="text-ink">{state.closures[0].name}</p>
              <p className="text-muted">{closureKind(state.closures[0].source)}</p>
            </div>
          ) : null}
          {detection ? (
            <div className="mt-2 space-y-1 text-[13px] leading-5">
              <Row label="Class" value={titleCase(detection.class)} />
              <Row label="Confidence" value={detection.confidence == null ? "Not measured" : detection.confidence.toFixed(2)} />
              <Row label="Verification" value={titleCase(detection.review_status)} />
              <Row label="Source" value={detection.inference_mode === "mock" ? "Scenario fixture" : detection.inference_mode} />
              <p className="text-[12px] leading-5 text-muted">{detection.confidence_note || detection.map_note}</p>
            </div>
          ) : null}
        </Disclosure>

        <Disclosure title="Satellite imagery">
          <ImageryTabs state={state} onShowImagery={onShowImagery} />
        </Disclosure>

        <Disclosure key={showExplanation ? "explained" : "unexplained"} title="Nemotron explanation" defaultOpen={showExplanation}>
          {showExplanation && state.explanation ? (
            <div className="space-y-2 text-[13px] leading-5">
              <p className="text-[12px] text-faint">{explanationLabel(state.explanation.inference_mode)}</p>
              {state.explanation.summary ? <p>{state.explanation.summary}</p> : null}
              {state.explanation.access ? <p className="text-muted">{state.explanation.access}</p> : null}
            </div>
          ) : (
            <p className="text-[13px] leading-5 text-muted">
              {incident?.source === "fixture"
                ? "Nemotron has not reviewed this queue item. It is a labeled demo report."
                : state.ml.detail}
            </p>
          )}
        </Disclosure>

        <Disclosure title="Uncertainty">
          <ul className="space-y-1.5 text-[12px] leading-5 text-muted">
            {(state.explanation?.uncertainties ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
            <li>{state.system.graph_note}</li>
            <li>{state.imagery.alignment_note}</li>
            <li>{state.system.disclaimer}</li>
          </ul>
        </Disclosure>

        <Disclosure title="Human review">
          <p className="text-[13px] leading-5">{state.review.note}</p>
          <p className="mt-1 text-[12px] leading-5 text-muted capitalize">{state.review.status.replaceAll("_", " ")}</p>
          <button
            type="button"
            disabled={busy || state.review.status !== "requested"}
            onClick={onAcknowledge}
            className="mt-3 h-8 w-full rounded-md bg-elevated text-[13px] text-ink disabled:opacity-40"
          >
            {state.review.status === "acknowledged" ? "Acknowledged" : "Acknowledge review"}
          </button>
        </Disclosure>
      </div>
    </aside>
  );
}

function ImageryTabs({ state, onShowImagery }: { state: AppState; onShowImagery: (which: "before" | "after") => void }) {
  const [which, setWhich] = useState<"before" | "after">("after");
  const layer = state.imagery[which];
  return (
    <div>
      <div className="grid grid-cols-2 rounded-md bg-elevated p-0.5 text-[12px]">
        {(["before", "after"] as const).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setWhich(item)}
            className={`h-6 rounded capitalize ${which === item ? "bg-surface text-ink" : "text-muted"}`}
          >
            {state.imagery[item].label}
          </button>
        ))}
      </div>
      <div className="mt-2 space-y-1 text-[12px] leading-5 text-muted">
        <p>{layer.attribution}</p>
        <p>Mosaic date {layer.release_date}</p>
        <p>{state.imagery.alignment_note}</p>
      </div>
      <button type="button" onClick={() => onShowImagery(which)} className="mt-2 h-8 w-full rounded-md bg-elevated text-[12px] text-ink">
        Show mosaic on map
      </button>
    </div>
  );
}

function Disclosure({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-t border-line">
      <button type="button" onClick={() => setOpen((value) => !value)} className="flex w-full items-center justify-between px-3 py-2.5 text-left">
        <span className="text-[13px] text-ink">{title}</span>
        <ChevronDown size={14} className={`text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open ? <div className="px-3 pb-3">{children}</div> : null}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className="truncate text-right text-ink">{value}</span>
    </div>
  );
}

function accessHeadline(status: AppState["routes"]["status"]): string {
  if (status === "proposed") return "Candidate route on the open graph";
  if (status === "invalidated") return "Candidate route withdrawn";
  if (status === "rerouted") return "Replacement route on the open graph";
  if (status === "unreachable") return "Potentially isolated";
  return "No corridor route yet";
}

function accessDetail(state: AppState): string {
  if (state.routes.status === "unreachable") return "No available path in the current road graph. Nothing has been dispatched.";
  if (state.routes.conflicts) return "The candidate still uses a segment this simulation has closed.";
  if (state.routes.status === "rerouted") return "Calculated again after the simulated closure. This does not mean the road is open in the field.";
  if (state.routes.status === "proposed") return "Shortest path on the current OpenStreetMap graph.";
  return "Run the scenario to calculate the first candidate route.";
}

function routeHeadline(status: CalculatedRoute["status"]): string {
  if (status === "ok") return "Candidate access from Rescue 4";
  if (status === "unreachable") return "Potentially isolated from Rescue 4";
  return "Could not snap onto the loaded road graph";
}

function explanationLabel(mode: string): string {
  if (mode === "real") return "Model response";
  if (mode === "unavailable") return "Model unavailable";
  return "Local template. Nemotron was not called.";
}
