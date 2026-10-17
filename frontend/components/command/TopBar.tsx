"use client";

import { useEffect, useState } from "react";
import { localTime, scenarioTime } from "@/lib/format";
import type { AppState } from "@/lib/types";

const ML_LABEL: Record<string, string> = {
  mock: "ML mock",
  real: "ML live",
  unavailable: "ML offline",
  unchecked: "ML idle",
};

export function TopBar({
  state,
  busy,
  onAdvance,
  onReset,
}: {
  state: AppState;
  busy: boolean;
  onAdvance: () => void;
  onReset: () => void;
}) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const done = state.scenario.step >= state.scenario.step_count - 1;
  const ml = ML_LABEL[state.ml.mode] ?? state.ml.mode;

  return (
    <header className="flex h-[58px] shrink-0 items-center gap-5 border-b border-line bg-panel px-3">
      <div className="w-[210px] shrink-0">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 bg-critical" />
          <span className="text-[13px] font-semibold tracking-[0.22em]">SOSORA</span>
        </div>
        <p className="mt-0.5 text-[11px] text-muted">Swannanoa · Helene case study</p>
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-[10px] tracking-[0.16em] text-faint">
          STEP {String(state.scenario.step + 1).padStart(2, "0")} / {String(state.scenario.step_count).padStart(2, "0")}
          <span className="mx-2 text-line">/</span>
          SIMULATED
        </p>
        <p className="truncate text-[15px] font-medium leading-tight">{state.scenario.step_title}</p>
      </div>

      <div className="hidden items-center gap-4 xl:flex">
        <Stamp label="Scenario" value={scenarioTime(state.scenario.clock)} />
        <Stamp label="Local" value={localTime(now)} />
        <Stamp label="Graph" value={`${state.system.graph_edges.toLocaleString()} edges`} />
        <span className="border border-line px-2 py-1 text-[10px] tracking-[0.14em] text-info uppercase">{ml}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onReset}
          disabled={busy}
          className="h-8 border border-line px-3 text-[12px] text-muted hover:text-ink disabled:opacity-40"
        >
          Reset
        </button>
        <button
          type="button"
          onClick={onAdvance}
          disabled={busy || done}
          className="h-8 bg-info px-3 text-[12px] font-semibold text-bg disabled:opacity-40"
        >
          {done ? "Complete" : `Advance · ${state.scenario.next_title}`}
        </button>
      </div>
    </header>
  );
}

function Stamp({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] tracking-[0.14em] text-faint uppercase">{label}</p>
      <p className="mono text-[12px] text-ink">{value}</p>
    </div>
  );
}
