"use client";

import { agentStatusLabel } from "@/lib/ops";
import { Play } from "lucide-react";
import type { AppState, MapPhase } from "@/lib/types";

export function Header({
  state,
  mapPhase,
  busy,
  agentState,
  onRun,
}: {
  state: AppState;
  mapPhase: MapPhase;
  playing?: boolean;
  busy: boolean;
  agentState: ReturnType<typeof import("@/lib/ops").agentStatus>;
  onRun: () => void;
}) {
  return (
    <header className="ops-header">
      <div className="brand">
        <div className="brand-mark" aria-hidden>
          ≋
        </div>
        <div>
          <strong>
            SOS<span>ora</span>
          </strong>
          <small>RESCUE INTELLIGENCE</small>
        </div>
      </div>
      <div className="header-center">
        Swannanoa operations drill{" "}
        <span className="text-faint">· Western North Carolina</span>
        <span className="simulation-tag">[SIMULATED]</span>
      </div>
      <div className="header-actions">
        <Status
          label={
            mapPhase === "ready"
              ? "Map"
              : mapPhase === "error"
                ? "Map offline"
                : "Map loading"
          }
          tone={mapPhase === "ready" ? "bg-route" : "bg-warning"}
          title="Map rendering status"
        />
        <Status
          label={
            state.ml.mode === "real"
              ? "Model online"
              : state.system.demo_mode
                ? "Model cached"
                : "Model idle"
          }
          tone={state.ml.mode === "real" ? "bg-route" : "bg-faint"}
          title={state.ml.detail}
        />
        <Status
          label={`Agent: ${agentStatusLabel(agentState)}`}
          textTone={agentState === "needs review" ? "text-warning" : agentState === "action required" ? "text-critical" : agentState === "ready for operator" ? "text-accent" : ""}
          tone={
            agentState === "working"
              ? "bg-live animate-pulse"
              : agentState === "needs review"
                ? "bg-warning"
                : agentState === "action required" ? "bg-critical" : "bg-route"
          }
          title="Radio agent processing status"
        />
        <button
          className="primary-button"
          onClick={onRun}
          disabled={busy || agentState === "working"}
        >
          <Play size={13} fill="currentColor" />
          Run demo
        </button>
      </div>
    </header>
  );
}
function Status({
  label,
  tone,
  title,
  textTone = "",
}: {
  textTone?: string;
  label: string;
  tone: string;
  title: string;
}) {
  return (
    <span title={title} className={`header-status ${textTone}`}>
      <i className={`h-1.5 w-1.5 rounded-full ${tone}`} />
      {label}
    </span>
  );
}
