"use client";

import { useEffect, useState } from "react";
import { useOps } from "@/hooks/useOps";
import { OpsMap } from "@/components/map/OpsMap";
import { IncidentRail } from "@/components/command/IncidentRail";
import { IntelRail } from "@/components/command/IntelRail";
import { Timeline } from "@/components/command/Timeline";
import { TopBar } from "@/components/command/TopBar";

export function CommandCenter() {
  const { state, roads, error, busy, advance, reset, acknowledge, injectSos, refresh } = useOps();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "ArrowRight") advance();
      if (event.key === "r" || event.key === "R") reset();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, reset]);

  if (!state || !roads) {
    return (
      <main className="flex h-screen items-center justify-center bg-bg">
        <div>
          <p className="text-[13px] font-semibold tracking-[0.22em]">SOSORA</p>
          <p className="mt-2 text-[13px] text-muted">{error ?? "Loading the Swannanoa road graph"}</p>
          <div className="boot-line mt-4" />
          {error ? (
            <button type="button" onClick={() => refresh()} className="mt-4 h-8 border border-line px-3 text-[12px]">
              Retry
            </button>
          ) : null}
        </div>
      </main>
    );
  }

  const selected = state.incidents.find((item) => item.id === selectedId) ?? state.incidents[0] ?? null;

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-bg text-ink">
      <TopBar state={state} busy={busy} onAdvance={advance} onReset={reset} />
      {error ? <p className="bg-critical/15 px-3 py-1 text-[12px] text-critical">{error}</p> : null}
      <div className="flex min-h-0 flex-1">
        <IncidentRail state={state} selectedId={selected?.id ?? null} onSelect={setSelectedId} onInject={injectSos} busy={busy} />
        <section className="relative min-w-0 flex-1">
          <OpsMap state={state} roads={roads} />
        </section>
        <IntelRail state={state} incident={selected} onAcknowledge={acknowledge} busy={busy} />
      </div>
      <Timeline state={state} />
    </main>
  );
}
