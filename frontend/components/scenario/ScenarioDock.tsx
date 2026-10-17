"use client";

import { ChevronUp, Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";
import { scenarioTime } from "@/lib/format";
import { STAGES, stageIndex } from "@/lib/stages";
import type { ScenarioEvent } from "@/lib/types";

export function ScenarioDock({
  step,
  playing,
  busy,
  events,
  timelineOpen,
  canPrev,
  canNext,
  onPrev,
  onNext,
  onTogglePlay,
  onReset,
  onToggleTimeline,
}: {
  step: number;
  playing: boolean;
  busy: boolean;
  events: ScenarioEvent[];
  timelineOpen: boolean;
  canPrev: boolean;
  canNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onTogglePlay: () => void;
  onReset: () => void;
  onToggleTimeline: () => void;
}) {
  const current = stageIndex(step);

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-3 z-20 flex justify-center px-3">
      <div className="pointer-events-auto w-full max-w-[560px] overflow-hidden rounded-lg border border-line bg-surface/95">
        {timelineOpen ? (
          <ol className="max-h-36 overflow-y-auto border-b border-line px-3 py-2">
            {events.length === 0 ? (
              <li className="text-[12px] text-muted">No events yet.</li>
            ) : (
              events.map((event) => (
                <li key={event.id} className="flex gap-3 py-1 text-[12px] leading-5">
                  <time className="w-[92px] shrink-0 text-faint">{scenarioTime(event.at)}</time>
                  <span className="min-w-0 text-muted">{event.message}</span>
                </li>
              ))
            )}
          </ol>
        ) : null}
        <div className="flex items-center gap-2 px-2.5 py-2">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] text-ink">{current >= 0 ? STAGES[current].label : "Standby"}</p>
            <div className="mt-1.5 flex gap-1">
              {STAGES.map((stage, index) => (
                <span
                  key={stage.id}
                  title={stage.label}
                  className={`h-1 flex-1 rounded-full ${index === current ? "bg-accent-soft" : index < current ? "bg-ink/50" : "bg-white/10"}`}
                />
              ))}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-0.5">
            <DockButton label="Previous stage" disabled={!canPrev || busy} onClick={onPrev}>
              <SkipBack size={14} />
            </DockButton>
            <DockButton label={playing ? "Pause scenario" : "Play scenario"} disabled={busy} onClick={onTogglePlay}>
              {playing ? <Pause size={14} /> : <Play size={14} />}
            </DockButton>
            <DockButton label="Next stage" disabled={!canNext || busy} onClick={onNext}>
              <SkipForward size={14} />
            </DockButton>
            <DockButton label="Reset scenario" disabled={busy} onClick={onReset}>
              <RotateCcw size={14} />
            </DockButton>
            <DockButton label={timelineOpen ? "Hide timeline" : "Show timeline"} onClick={onToggleTimeline}>
              <ChevronUp size={14} className={timelineOpen ? "" : "rotate-180"} />
            </DockButton>
          </div>
        </div>
      </div>
    </div>
  );
}

function DockButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-elevated hover:text-ink disabled:opacity-35"
    >
      {children}
    </button>
  );
}
