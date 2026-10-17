"use client";

import type { AppState } from "@/lib/types";

export function Timeline({ state }: { state: AppState }) {
  const latest = state.events[state.events.length - 1];
  return (
    <footer className="flex h-[92px] shrink-0 border-t border-line bg-panel">
      <div className="flex w-[300px] shrink-0 flex-col justify-center border-r border-line px-3">
        <p className="text-[10px] tracking-[0.16em] text-faint uppercase">Timeline</p>
        <p className="mt-1 line-clamp-2 text-[12px] leading-snug">{latest?.message}</p>
      </div>
      <ol className="flex min-w-0 flex-1 items-center gap-1 px-3">
        {state.steps.map((step) => {
          const done = step.index < state.scenario.step;
          const current = step.index === state.scenario.step;
          return (
            <li key={step.id} className="min-w-0 flex-1">
              <div className="flex items-center gap-1">
                <span
                  className={`h-1.5 w-1.5 shrink-0 ${
                    current ? "bg-info shadow-[0_0_0_3px_rgba(106,215,255,0.2)]" : done ? "bg-ink" : "bg-faint/40"
                  }`}
                />
                <span className={`h-px flex-1 ${done ? "bg-ink/50" : "bg-line"}`} />
              </div>
              <p className={`mt-1 truncate text-[10px] ${current ? "text-info" : "text-muted"}`}>{step.label}</p>
            </li>
          );
        })}
      </ol>
    </footer>
  );
}
