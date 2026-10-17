"use client";

import { Play } from "lucide-react";
import { stageLabel } from "@/lib/stages";
import type { AppState, MapPhase } from "@/lib/types";

const MODEL_LABEL: Record<string, string> = {
  mock: "Model demo",
  real: "Model live",
  unavailable: "Model offline",
  unchecked: "Model idle",
};

export function Header({
  state,
  mapPhase,
  playing,
  busy,
  onRun,
}: {
  state: AppState;
  mapPhase: MapPhase;
  playing: boolean;
  busy: boolean;
  onRun: () => void;
}) {
  const mapLabel = mapPhase === "ready" ? "Map live" : mapPhase === "error" ? "Map unavailable" : "Map loading";
  const mapTone = mapPhase === "ready" ? "bg-route" : mapPhase === "error" ? "bg-critical" : "bg-warning";
  const model = MODEL_LABEL[state.ml.mode] ?? state.ml.mode;
  const modelTone = state.ml.mode === "real" ? "bg-route" : state.ml.mode === "unavailable" ? "bg-warning" : "bg-faint";
  const done = state.scenario.step >= state.scenario.step_count - 1;

  return (
    <header className="grid h-[60px] shrink-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 border-b border-line bg-surface px-4">
      <div className="flex items-center gap-2.5">
        <p className="text-[18px] leading-none font-semibold tracking-tight">
          <span className="text-ink">SOS</span>
          <span className="font-medium text-muted">ora</span>
        </p>
        <span className="hidden h-4 w-px bg-line sm:block" />
        <p className="hidden text-[12px] text-muted sm:block">Rescue Intelligence</p>
      </div>

      <div className="min-w-0 text-center">
        <p className="truncate text-[14px] font-medium text-ink">Hurricane Helene</p>
        <p className="truncate text-[12px] text-muted">
          Asheville / Swannanoa, North Carolina
          <span className="mx-1.5 text-faint">·</span>
          {playing ? "Playing" : stageLabel(state.scenario.step)}
          <span className="mx-1.5 text-faint">·</span>
          Simulated
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Status label={mapLabel} tone={mapTone} title={mapLabel} />
        <Status label={model} tone={modelTone} title={state.ml.detail} />
        <button
          type="button"
          onClick={onRun}
          disabled={busy}
          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-accent px-3 text-[13px] font-medium text-ink disabled:opacity-50"
        >
          <Play size={13} fill="currentColor" />
          {done && !playing ? "Replay" : "Run scenario"}
        </button>
      </div>
    </header>
  );
}

function Status({ label, tone, title }: { label: string; tone: string; title: string }) {
  return (
    <span title={title} className="hidden items-center gap-1.5 text-[12px] text-muted lg:inline-flex">
      <i className={`h-1.5 w-1.5 rounded-full ${tone}`} />
      {label}
    </span>
  );
}
