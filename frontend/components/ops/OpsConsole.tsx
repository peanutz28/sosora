"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { TerminalRow } from "@/components/ops/TerminalRow";
import { Radio, ChevronDown, Activity, ShieldCheck } from "lucide-react";
import {
  agentStatus,
  accessCounters,
  agentStatusLabel,
  agentTraceBadge,
  eventKey,
  latestAssessment,
  reviewCandidates,
  traceSummary,
} from "@/lib/ops";
import type { AppState, BridgeCandidate, OpsEvent } from "@/lib/types";

export type DrillAction = "seed" | "beacon" | "responder" | "dot" | "water" | "imagery";
export function OpsConsole({
  state,
  stream,
  working,
  socketLive,
  seeded,
  busy,
  onAction,
  onConfirm,
}: {
  state: AppState;
  stream: OpsEvent[];
  working: boolean;
  socketLive: boolean;
  seeded: boolean;
  busy: boolean;
  onAction: (action: DrillAction) => void;
  onConfirm: (candidate: BridgeCandidate, radioId: string) => void;
}) {
  const traceRef = useRef<HTMLDivElement>(null);
  const scrollTrace = useCallback(() => {
    const list = traceRef.current;
    if (list) requestAnimationFrame(() => { list.scrollTop = list.scrollHeight; });
  }, []);
  const [collapsed, setCollapsed] = useState(false);
  const [controls, setControls] = useState(true);
  const [history, setHistory] = useState(false);
  const [inputs, setInputs] = useState(false);
  const [wave, setWave] = useState(false);
  const assessment = latestAssessment(stream);
  const status = agentStatus(working, assessment, stream);
  const traceBadge = agentTraceBadge(stream, state.system.demo_mode);
  const candidates = reviewCandidates(stream, assessment);
  const radioId = [...stream]
    .reverse()
    .find((event) => event.kind === "radio_received")?.radio_id;
  const { cutOff, reachable, blocked } = accessCounters(state, stream);
  const feed = stream
    .filter((event) =>
      [
        "radio_received",
        "voice_transcribed",
        "radio_parsed",
        "sensor_reading",
        "radio_location_confirmed",
      ].includes(event.kind),
    )
    .reverse();
  const calls = stream
    .filter((event) => event.kind === "agent_tool_call")
    .slice(-24);
  const errors = stream
    .filter((event) => event.kind === "agent_error")
    .slice(-1);
  const newest = feed[0] ? eventKey(feed[0]) : "";
  useEffect(() => {
    if (!newest) return;
    setWave(true);
    const timer = setTimeout(() => setWave(false), 3000);
    return () => clearTimeout(timer);
  }, [newest]);
  const actions = useRef(onAction);
  actions.current = onAction;
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (
        event.repeat ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        (event.target instanceof HTMLElement &&
          (event.target.isContentEditable ||
            /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)))
      )
        return;
      const action = (
        {
          s: "seed",
          b: "beacon",
          r: "responder",
          d: "dot",
          w: "water",
          i: "imagery",
        } as Record<string, DrillAction>
      )[event.key.toLowerCase()];
      if (action && !working && !busy && (seeded || action === "seed" || action === "imagery")) {
        event.preventDefault();
        actions.current(action);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [working, busy, seeded]);
  return (
    <aside className={`ops-console ${collapsed ? "console-collapsed" : ""}`} aria-label="Operations console">
      <div className="console-heading">
        <div>
          <p className="eyebrow">COMMAND INTELLIGENCE</p>
          <h2 className="font-display">Every report. One picture.</h2>
        </div>
        <button className="icon-control" aria-label={collapsed ? "Expand intelligence" : "Collapse intelligence"} onClick={() => setCollapsed(!collapsed)}><ChevronDown size={17} className={collapsed ? "" : "rotate-180"} /></button>
      </div>
      <div className="summary-grid">
        <Kpi
          label="Families cut off"
          value={cutOff}
          tone="text-critical"
          animate
        />
        <Kpi label="SOS reachable" value={reachable} tone="text-accent" />
        <Kpi
          label="Roads blocked"
          value={blocked}
          tone="text-ink"
        />
        <div className="kpi">
          <span>Agent</span>
          <b
            className={`agent-kpi ${status === "working" ? "text-live" : status === "needs review" ? "text-warning" : status === "action required" ? "text-critical" : "text-accent"}`}
          >
            <i className={`status-dot ${working ? "working" : ""}`} />
            {agentStatusLabel(status)}
          </b>
          <small>
            {state.system.demo_mode
              ? "Cached demo trace"
              : "Nemotron Lightning"}
          </small>
        </div>
      </div>
      <section className="drill-section">
        <button
          className="section-heading"
          onClick={() => setControls(!controls)}
          aria-expanded={controls}
        >
          <span>
            DRILL CONTROLS <span className="pill simulated">SIMULATED</span>
          </span>
          <ChevronDown size={13} className={controls ? "rotate-180" : ""} />
        </button>
        {controls && (
          <div className="drill-buttons">
            {(
              [
                ["S", "Seed drill", "seed"],
                ["B", "Beacon report", "beacon"],
                ["R", "Responder radio", "responder"],
                ["D", "DOT says open", "dot"],
                ["W", "Water spike", "water"],
                ["I", "Imagery offline", "imagery"],
              ] as const
            ).map(([key, label, action]) => (
              <button
                key={key}
                disabled={busy || working || (!seeded && action !== "seed" && action !== "imagery")}
                aria-pressed={action === "imagery" ? !!state.imagery.offline : undefined}
                onClick={() => onAction(action)}
              >
                <kbd>{key}</kbd>
                {label}{action === "imagery" && state.imagery.offline ? " · ON" : ""}
              </button>
            ))}
          </div>
        )}
      </section>
      {candidates.length > 0 && radioId && (
        <section className="review-card row-in">
          <p className="eyebrow">LOCATION NEEDS REVIEW</p>
          <h3>Which bridge did they mean?</h3>
          <p>
            Multiple real crossings match. Confirm the location before changing
            road status.
          </p>
          {candidates.map((candidate) => (
            <button
              key={candidate.id}
              disabled={working}
              onClick={() => onConfirm(candidate, radioId)}
            >
              <b>{candidate.label}</b>
              <span>
                Confirm bridge {candidate.label}
                <small>
                  {candidate.centroid[1].toFixed(5)},{" "}
                  {candidate.centroid[0].toFixed(5)}
                </small>
              </span>
              <span>↗</span>
            </button>
          ))}
        </section>
      )}
      <section className="console-section radio-section">
        <div className="section-heading">
          <span>
            <Radio size={13} />
            RADIO FEED
          </span>
          <span className="stream-status">
            <i
              className={`status-dot ${socketLive ? "text-accent" : "text-warning"}`}
            />
            {socketLive ? "Connected" : "Reconnecting"}
          </span>
        </div>
        {!feed.length ? (
          <div className="console-empty">
            <span className="empty-radio">
              <Radio size={22} />
            </span>
            <p>Listening for field reports</p>
            <small>Seed the drill, then send a Beacon report.</small>
          </div>
        ) : (
          (history ? feed.slice(0, 8) : feed.slice(0, 1)).map(
            (event, index) => {
              const received = stream.find(
                (item) =>
                  item.kind === "radio_received" &&
                  item.radio_id === event.radio_id,
              );
              const source =
                event.beacon_id ||
                received?.source_type === "beacon" ||
                event.source_type === "beacon"
                  ? "Beacon"
                  : event.unit || received?.unit || "Field radio";
              return (
                <article key={eventKey(event)} className="radio-entry row-in">
                  <div className="radio-meta">
                    <b>{source}</b>
                    <span className="pill simulated">SIMULATED</span>
                    <time>{eventTime(event.at)}</time>
                    {index === 0 && wave && (
                      <span className="wave" aria-label="New report">
                        <span />
                        <span />
                        <span />
                        <span />
                        <span />
                      </span>
                    )}
                  </div>
                  <p>
                    “
                    {event.kind === "radio_parsed"
                      ? String(
                          event.parse?.raw ||
                            received?.message ||
                            event.message,
                        )
                      : event.text || event.message}
                    ”
                  </p>
                  {event.parse && (
                    <div className="parse-pills">
                      {["event_type", "road_name", "urgency"].map((key) =>
                        event.parse?.[key] ? (
                          <span
                            key={key}
                            className={`pill ${key === "urgency" ? "high" : ""}`}
                          >
                            {String(event.parse[key]).replaceAll("_", " ")}
                          </span>
                        ) : null,
                      )}
                    </div>
                  )}
                </article>
              );
            },
          )
        )}
        {feed.length > 1 && (
          <button
            className="history-button"
            onClick={() => setHistory(!history)}
          >
            {history ? "Collapse history" : `View ${feed.length} radio events`}{" "}
            <ChevronDown size={11} />
          </button>
        )}
      </section>
      <section className="console-section trace-section">
        <div className="section-heading">
          <span>
            <Activity size={13} />
            AGENT TRACE
          </span>
          <button
            className="trace-input-toggle"
            onClick={() => setInputs(!inputs)}
            title="Show or hide full tool inputs"
          >
            {calls.length
              ? `${calls.length} calls · ${inputs ? "Hide" : "Show"} inputs`
              : "AWAITING REPORT"}
          </button>
        </div>
        <div className="trace-model-badge" title={traceBadge.title}>{traceBadge.label}</div>
        {!calls.length && (
          <p className="empty-note">
            Resolve location → check evidence → update road → recompute access.
          </p>
        )}
        <div className="tool-list" ref={traceRef} role="log" aria-label="Agent tool calls" aria-live="polite">
          {calls.map((call, index) => {
            const result = stream.find(
              (event) =>
                event.kind === "agent_tool_result" &&
                event.call_id === call.call_id &&
                event.tool === call.tool &&
                event.at >= call.at,
            );
            return (
              <TerminalRow key={eventKey(call)} call={call} result={result} index={index} newest={index === calls.length - 1} inputs={inputs} onProgress={scrollTrace} />
            );
          })}
        </div>
        {errors.map((event) => (
          <p key={eventKey(event)} className="text-critical text-xs">
            {traceSummary(event)}
          </p>
        ))}
      </section>
      <section className="assessment-card">
        <div className="section-heading">
          <span>
            <ShieldCheck size={14} />
            LATEST ASSESSMENT
          </span>
          {assessment && (
            <span className={`pill ${status === "needs review" ? "unverified" : status === "action required" ? "high" : "operator-signoff"}`}>
              {status === "needs review" ? "Human review required" : status === "action required" ? "Assessment incomplete" : "Operator sign-off"}
            </span>
          )}
        </div>
        <p>
          {assessment?.summary ||
            "The map is ready. A field report will trigger a new access assessment."}
        </p>
        {assessment && (
          <>
            <div className="affected-ids">
              {assessment.affected_incident_ids.map((id) => (
                <span className="pill high" key={id}>
                  {id}
                </span>
              ))}
            </div>

          </>
        )}
      </section>
      <p className="console-disclaimer">
        Decision support, never automatic dispatch.
        <br />
        Road access is calculated; field safety is unverified.
      </p>
    </aside>
  );
}
function Kpi({
  label,
  value,
  tone,
  animate = false,
}: {
  label: string;
  value: number;
  tone: string;
  animate?: boolean;
}) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    if (!animate) return;
    if (value === 0) { setShown(0); return; }
    let frame = 0;
    setShown(0);
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / 800);
      setShown(Math.ceil(value * progress));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, animate]);
  const displayed = animate ? shown : value;
  return (
    <div className={`kpi ${animate && shown > 0 ? "kpi-alert" : ""}`}>
      <span>{label}</span>
      <b className={`font-display ${displayed === 0 ? "text-faint" : tone}`} aria-label={`${label}: ${value}`}>
        {displayed.toString().padStart(2, "0")}
      </b>
      <small>
        {label === "Families cut off"
          ? "SOS incidents without a road route"
          : label === "SOS reachable"
            ? "Routes in the current graph"
            : "Physical road segments"}
      </small>
    </div>
  );
}
function eventTime(at: string) {
  const date = new Date(at);
  return Number.isNaN(date.valueOf())
    ? "—"
    : date.toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
}
