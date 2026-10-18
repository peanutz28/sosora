"use client";

import { useMemo, useState } from "react";
import {
  PanelLeftClose,
  Search,
  Plus,
  ArrowUpRight,
  Users,
} from "lucide-react";
import { roadAccess } from "@/lib/access";
import { peopleLabel, scenarioTime } from "@/lib/format";
import type { LngLat, QueueIncident } from "@/lib/types";

type Filter = "all" | "critical" | "cut off";
export function IncidentSidebar({
  incidents,
  selectedId,
  busy,
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
  const visible = useMemo(
    () =>
      incidents.filter((incident) => {
        if (filter === "critical" && incident.urgency !== "critical")
          return false;
        if (filter === "cut off" && roadAccess(incident).status !== "lost")
          return false;
        return `${incident.id} ${incident.title} ${incident.message}`
          .toLowerCase()
          .includes(query.trim().toLowerCase());
      }),
    [filter, incidents, query],
  );
  return (
    <aside className="incident-rail">
      <div className="rail-heading">
        <div>
          <p className="eyebrow">OPERATIONS</p>
          <h1 className="font-display">
            Incident log <span>{incidents.length}</span>
          </h1>
        </div>
        <button
          aria-label="Collapse incidents"
          className="icon-control"
          onClick={onCollapse}
        >
          <PanelLeftClose size={16} />
        </button>
      </div>
      <label className="incident-search">
        <Search size={14} />
        <input
          placeholder="Search incidents"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <span className="font-mono">⌕</span>
      </label>
      <div className="segmented">
        {(["all", "critical", "cut off"] as const).map((value) => (
          <button
            key={value}
            className={filter === value ? "active" : ""}
            onClick={() => setFilter(value)}
          >
            {value}
          </button>
        ))}
      </div>
      <div className="incident-scroll">
        {visible.length === 0 && (
          <p className="empty-note">No incidents match this filter.</p>
        )}
        {visible.map((incident) => {
          const access = roadAccess(incident);
          return (
            <button
              key={incident.id}
              className={`incident-card ${incident.urgency === "critical" ? "critical" : ""} ${selectedId === incident.id ? "selected" : ""}`}
              onClick={() => onSelect(incident.id)}
            >
              <div className="incident-top">
                <b className="font-mono">{incident.id}</b>
                <span className={`priority ${incident.urgency}`}>
                  ● {incident.urgency}
                </span>
              </div>
              <h2>{incident.title.replace(/^\[SIMULATED\]\s*/i, "")}</h2>
              <p className="incident-message">
                {incident.message
                  .replace(/^\[SIMULATED\]\s*/i, "")
                  .split(". ")
                  .slice(1)
                  .join(". ") ||
                  incident.message.replace(/^\[SIMULATED\]\s*/i, "")}
              </p>
              <div className="incident-meta">
                <span>
                  <Users size={12} />
                  {peopleLabel(incident.people_affected)}
                </span>
                <time>{scenarioTime(incident.created_at)}</time>
              </div>
              <div className="incident-access">
                <span className={`access-${access.status}`}>
                  {access.status === "lost"
                    ? "⊘"
                    : access.status === "available"
                      ? "↗"
                      : "○"}{" "}
                  {access.label}
                </span>
                <ArrowUpRight size={13} />
              </div>
              <span className="pill simulated">SIMULATED</span>
            </button>
          );
        })}
      </div>
      <div className="rail-footer">
        {composer ? (
          <div className="space-y-2">
            <textarea
              aria-label="SOS message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Describe the situation"
              rows={3}
            />
            <input
              aria-label="People affected"
              type="number"
              min={1}
              value={people}
              onChange={(e) => setPeople(e.target.value)}
            />
            <button
              className="outline-button w-full"
              onClick={() => onPlace(!placeMode)}
            >
              {draftPoint ? "Location set" : "Click map to place"}
            </button>
            <div className="flex gap-2">
              <button
                className="outline-button flex-1"
                onClick={() => {
                  setComposer(false);
                  onPlace(false);
                }}
              >
                Cancel
              </button>
              <button
                className="primary-button flex-1"
                disabled={
                  busy ||
                  !draftPoint ||
                  !message.trim() ||
                  !Number.isFinite(Number(people)) ||
                  Number(people) < 1
                }
                onClick={() => {
                  if (!draftPoint) return;
                  onCreate({
                    message: "[SIMULATED] " + message.trim(),
                    people: Number(people),
                    point: draftPoint,
                  });
                  setMessage("");
                  setComposer(false);
                  onPlace(false);
                }}
              >
                Save SOS
              </button>
            </div>
          </div>
        ) : (
          <button className="new-sos" onClick={() => setComposer(true)}>
            <Plus size={15} />
            Create drill SOS
          </button>
        )}
        <p>
          Simulated reports. Real road geometry.
          <br />
          Operator review before any response.
        </p>
      </div>
    </aside>
  );
}
