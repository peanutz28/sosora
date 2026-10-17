"use client";

import { useMemo, useState } from "react";
import { PanelLeftClose, Search } from "lucide-react";
import { peopleLabel, scenarioTime } from "@/lib/format";
import type { LngLat, QueueIncident } from "@/lib/types";

type Filter = "all" | "critical" | "unresolved";

export function IncidentSidebar({
  incidents,
  selectedId,
  busy,
  reviewStatus,
  placeMode,
  draftPoint,
  onSelect,
  onCollapse,
  onCreate,
  onPlace,
}: {
  incidents: QueueIncident[];
  selectedId: string | null;
  busy: boolean;
  reviewStatus: string;
  placeMode: boolean;
  draftPoint: LngLat | null;
  onSelect: (id: string) => void;
  onCollapse: () => void;
  onCreate: (input: { message: string; people: number; point: LngLat }) => void;
  onPlace: (active: boolean) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [composer, setComposer] = useState(false);
  const [message, setMessage] = useState("");
  const [people, setPeople] = useState("1");

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return incidents.filter((incident) => {
      if (filter === "critical" && incident.urgency !== "critical") return false;
      if (filter === "unresolved" && incident.verification === "verified") return false;
      if (!needle) return true;
      const haystack = `${incident.id} ${incident.title} ${incident.location} ${incident.message}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [filter, incidents, query]);

  const submit = () => {
    const count = Number(people);
    if (!draftPoint || !message.trim() || !Number.isFinite(count)) return;
    onCreate({ message: message.trim(), people: count, point: draftPoint });
    setMessage("");
    setPeople("1");
    setComposer(false);
    onPlace(false);
  };

  return (
    <aside className="flex w-[272px] shrink-0 flex-col border-r border-line bg-surface">
      <div className="flex items-center justify-between px-3 pt-3 pb-2">
        <div className="flex items-baseline gap-2">
          <h1 className="text-[14px] font-medium">Incidents</h1>
          <span className="text-[12px] text-muted">{incidents.length}</span>
        </div>
        <button type="button" aria-label="Collapse incidents" onClick={onCollapse} className="grid h-7 w-7 place-items-center text-muted hover:text-ink">
          <PanelLeftClose size={15} />
        </button>
      </div>

      <div className="px-3 pb-2">
        <label className="flex h-8 items-center gap-2 rounded-md bg-elevated px-2">
          <Search size={13} className="shrink-0 text-faint" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search incidents"
            className="w-full bg-transparent text-[13px] outline-none placeholder:text-faint"
          />
        </label>
        <div className="mt-2 grid grid-cols-3 rounded-md bg-elevated p-0.5 text-[12px]">
          {(["all", "critical", "unresolved"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={`h-6 rounded capitalize ${filter === item ? "bg-surface text-ink" : "text-muted"}`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {visible.length === 0 ? (
          <p className="px-3 py-6 text-[13px] text-muted">No incidents match.</p>
        ) : (
          visible.map((incident) => (
            <button
              key={incident.id}
              type="button"
              onClick={() => onSelect(incident.id)}
              className={`block w-full border-t border-line px-3 py-2.5 text-left ${
                incident.id === selectedId ? "bg-elevated" : "hover:bg-white/[0.02]"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-1.5">
                  <i className={`h-1.5 w-1.5 shrink-0 rounded-full ${tone(incident.urgency)}`} />
                  <span className="truncate text-[12px] text-muted">{incident.id}</span>
                </span>
                <span
                  className={`shrink-0 text-[11px] capitalize ${
                    incident.urgency === "critical" ? "text-critical" : incident.urgency === "high" ? "text-warning" : "text-muted"
                  }`}
                >
                  {incident.urgency}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-[13px] leading-5 text-ink">{incident.title}</p>
              <p className="mt-0.5 truncate text-[12px] text-muted">{incident.location}</p>
              <p className="mt-1 truncate text-[11px] text-faint">
                {peopleLabel(incident.people_affected)}
                <span className="mx-1">·</span>
                {incident.delivery_status}
                <span className="mx-1">·</span>
                {incident.verification}
                {incident.source === "backend" && reviewStatus !== "not_requested" ? ` · ${reviewStatus.replaceAll("_", " ")}` : ""}
                <span className="mx-1">·</span>
                {scenarioTime(incident.created_at)}
              </p>
            </button>
          ))
        )}
      </div>

      <div className="border-t border-line p-3">
        {composer ? (
          <div className="space-y-2">
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="What is happening?"
              rows={3}
              className="w-full resize-none rounded-md bg-elevated px-2 py-1.5 text-[13px] outline-none placeholder:text-faint"
            />
            <div className="flex items-center gap-2">
              <input
                value={people}
                onChange={(event) => setPeople(event.target.value)}
                inputMode="numeric"
                aria-label="People affected"
                className="h-8 w-16 rounded-md bg-elevated px-2 text-[13px] outline-none"
              />
              <button
                type="button"
                onClick={() => onPlace(!placeMode)}
                className={`h-8 flex-1 rounded-md px-2 text-[12px] ${placeMode ? "bg-accent text-ink" : "bg-elevated text-muted"}`}
              >
                {draftPoint ? "Location set" : "Click map to place"}
              </button>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setComposer(false);
                  onPlace(false);
                }}
                className="h-8 flex-1 rounded-md text-[12px] text-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy || !draftPoint || !message.trim()}
                onClick={submit}
                className="h-8 flex-1 rounded-md bg-accent text-[12px] text-ink disabled:opacity-40"
              >
                Add SOS
              </button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setComposer(true)} className="h-8 w-full rounded-md bg-elevated text-[13px] text-ink">
            New SOS
          </button>
        )}
      </div>
    </aside>
  );
}

function tone(urgency: QueueIncident["urgency"]): string {
  if (urgency === "critical") return "bg-critical";
  if (urgency === "high") return "bg-warning";
  return "bg-faint";
}
