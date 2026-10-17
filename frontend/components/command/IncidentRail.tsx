"use client";

import { useMemo, useState } from "react";
import { scenarioTime } from "@/lib/format";
import type { AppState, Incident } from "@/lib/types";

const STATS = [
  ["2,700+", "High-water rescues, Southeast US", "NHC tropical cyclone report, Helene"],
  ["6,900+", "NC road and bridge damage sites", "NC OSBM damage and needs assessment"],
  ["7.4M", "US power customers affected", "NHC tropical cyclone report, Helene"],
  ["1,000+", "Cell sites out at peak, western NC", "NC Commerce briefing, Jan 2025"],
];

export function IncidentRail({
  state,
  selectedId,
  onSelect,
  onInject,
  busy,
}: {
  state: AppState;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onInject: () => void;
  busy: boolean;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "critical" | "review">("all");
  const incidents = useMemo(() => {
    return state.incidents.filter((incident) => {
      const text = `${incident.id} ${incident.message} ${incident.source_id}`.toLowerCase();
      if (query && !text.includes(query.toLowerCase())) return false;
      if (filter === "critical" && incident.urgency !== "critical") return false;
      if (filter === "review" && state.review.status === "not_requested") return false;
      return true;
    });
  }, [filter, query, state.incidents, state.review.status]);

  return (
    <aside className="flex w-[300px] shrink-0 flex-col border-r border-line bg-panel">
      <div className="border-b border-line px-3 py-3">
        <p className="text-[10px] tracking-[0.16em] text-faint uppercase">Published impact · not this system</p>
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">
          {STATS.map(([value, label, source]) => (
            <p key={value} title={source} className="min-w-0">
              <span className="mono block text-[13px] text-ink">{value}</span>
              <span className="block text-[10px] leading-snug text-muted">{label}</span>
            </p>
          ))}
        </div>
      </div>

      <div className="border-b border-line px-3 py-2">
        <div className="flex items-center justify-between">
          <p className="text-[10px] tracking-[0.16em] text-faint uppercase">Incidents</p>
          <span className="mono text-[11px] text-muted">{state.incidents.length}</span>
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search reports"
          className="mt-2 w-full border-b border-line bg-transparent py-1 text-[12px] outline-none placeholder:text-faint"
        />
        <div className="mt-2 flex gap-3 text-[11px]">
          {(["all", "critical", "review"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={filter === item ? "text-info" : "text-muted"}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {incidents.length === 0 ? (
          <ObjectiveCard state={state} />
        ) : (
          incidents.map((incident) => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              active={incident.id === selectedId || (selectedId == null && incident.id === state.incidents[0]?.id)}
              review={state.review.status}
              onSelect={onSelect}
            />
          ))
        )}
      </div>

      <div className="border-t border-line p-3">
        <button
          type="button"
          disabled={busy}
          onClick={onInject}
          className="h-8 w-full border border-critical/50 text-[12px] text-critical hover:bg-critical/10 disabled:opacity-40"
        >
          Inject fictional SOS
        </button>
        <p className="mt-2 text-[10px] leading-snug text-faint">Same payload can be resent. A repeat keeps the original incident.</p>
      </div>
    </aside>
  );
}

function ObjectiveCard({ state }: { state: AppState }) {
  return (
    <article className="border-b border-line px-3 py-3">
      <p className="text-[10px] tracking-[0.14em] text-warning uppercase">No SOS yet</p>
      <h2 className="mt-1 text-[13px] font-medium">{state.objective.label}</h2>
      <p className="mono mt-1 text-[11px] text-muted">
        {state.objective.lat.toFixed(5)}, {state.objective.lon.toFixed(5)}
      </p>
      <p className="mt-2 text-[12px] leading-snug text-muted">
        Fictional planning point for Rescue 4. It is not a resident report until an SOS is stored.
      </p>
    </article>
  );
}

function IncidentCard({
  incident,
  active,
  review,
  onSelect,
}: {
  incident: Incident;
  active: boolean;
  review: string;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(incident.id)}
      className={`block w-full border-b border-line border-l-2 px-3 py-3 text-left ${
        incident.urgency === "critical" ? "border-l-critical" : "border-l-warning"
      } ${active ? "bg-white/[0.03]" : ""}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="mono text-[12px]">{incident.id}</span>
        <span className="text-[10px] tracking-[0.12em] text-critical uppercase">{incident.urgency}</span>
      </div>
      <p className="mt-1 line-clamp-3 text-[12px] leading-snug text-ink">{incident.message}</p>
      <p className="mt-2 text-[11px] text-muted">
        {incident.people_affected ?? "—"} people · {incident.source_id}
      </p>
      <p className="mono mt-1 text-[10px] text-faint">
        {incident.delivery_status} · {incident.verification} · {review.replaceAll("_", " ")} · {scenarioTime(incident.created_at)}
      </p>
    </button>
  );
}
