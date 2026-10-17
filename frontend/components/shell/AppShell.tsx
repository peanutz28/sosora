"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PanelLeftOpen } from "lucide-react";
import { IncidentSidebar } from "@/components/incidents/IncidentSidebar";
import { IntelPanel } from "@/components/intel/IntelPanel";
import { RescueMap } from "@/components/map/RescueMap";
import { ScenarioDock } from "@/components/scenario/ScenarioDock";
import { Header } from "@/components/shell/Header";
import { useOps } from "@/hooks/useOps";
import { calculateRoute } from "@/lib/api";
import { buildQueue } from "@/lib/queue";
import { nextTarget, prevTarget, stageIndex } from "@/lib/stages";
import type { AppState, BasemapMode, CalculatedRoute, LngLat, MapPhase } from "@/lib/types";

export function AppShell() {
  const { state, roads, error, roadsError, busy, reset, goto, acknowledge, createIncident, refresh } = useOps();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [intelOpen, setIntelOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [basemap, setBasemap] = useState<BasemapMode>("street");
  const [imageryTiles, setImageryTiles] = useState<string[] | null>(null);
  const [imageryLabel, setImageryLabel] = useState<string | null>(null);
  const [placeMode, setPlaceMode] = useState(false);
  const [draftPoint, setDraftPoint] = useState<LngLat | null>(null);
  const [focusRoute, setFocusRoute] = useState<CalculatedRoute | null>(null);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [mapPhase, setMapPhase] = useState<MapPhase>("loading");
  const [toast, setToast] = useState<string | null>(null);
  const [width, setWidth] = useState(1440);
  const [focusToken, setFocusToken] = useState(0);
  const sosFocus = useRef<string | null>(null);

  const incidents = useMemo(() => (state ? buildQueue(state) : []), [state]);
  const selected = incidents.find((item) => item.id === selectedId) ?? null;
  const narrow = width < 1180;

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (width < 1100) setRailOpen(false);
  }, [width < 1100]);

  useEffect(() => {
    if (!playing || !state || busy) return;
    const target = nextTarget(state.scenario.step);
    if (target == null) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => {
      void goto(target);
    }, state.scenario.step < 1 ? 200 : 3200);
    return () => window.clearTimeout(timer);
  }, [busy, goto, playing, state]);

  useEffect(() => {
    if (!state || state.scenario.step < 7) {
      sosFocus.current = null;
      return;
    }
    const arrived = state.incidents[state.incidents.length - 1];
    if (!arrived || sosFocus.current === arrived.id) return;
    sosFocus.current = arrived.id;
    setSelectedId(arrived.id);
    setIntelOpen(true);
    setFocusToken((value) => value + 1);
  }, [state]);

  useEffect(() => {
    if (!state) return;
    const note = stageNote(state);
    if (!note) return;
    setToast(note);
    const timer = window.setTimeout(() => setToast(null), 4600);
    return () => window.clearTimeout(timer);
  }, [state?.revision]);

  useEffect(() => {
    if (!state || !selected || selected.lon == null || selected.lat == null) {
      setFocusRoute(null);
      setRouteError(null);
      return;
    }
    let cancel = false;
    setRouteError(null);
    calculateRoute([state.rescue_unit.lon, state.rescue_unit.lat], [selected.lon, selected.lat])
      .then((route) => {
        if (!cancel) setFocusRoute(route);
      })
      .catch(() => {
        if (!cancel) {
          setFocusRoute(null);
          setRouteError("Route request did not reach the routing service.");
        }
      });
    return () => {
      cancel = true;
    };
  }, [selected, state]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (!state) return;
      if (event.key === "ArrowRight") {
        const target = nextTarget(state.scenario.step);
        if (target != null) void goto(target);
      }
      if (event.key === "ArrowLeft") {
        const target = prevTarget(state.scenario.step);
        if (target != null) void goto(target);
      }
      if (event.key === " ") {
        event.preventDefault();
        setPlaying((value) => !value);
      }
      if (event.key === "r" || event.key === "R") {
        setPlaying(false);
        void reset();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goto, reset, state]);

  const selectIncident = (id: string) => {
    setSelectedId(id);
    setIntelOpen(true);
  };

  const run = async () => {
    if (!state) return;
    if (state.scenario.step >= state.scenario.step_count - 1) {
      setPlaying(false);
      await reset();
    }
    setPlaying(true);
  };

  const step = state?.scenario.step ?? 0;

  if (!state) {
    return (
      <main className="flex h-dvh items-center justify-center bg-bg text-ink">
        <div className="max-w-sm text-center">
          <p className="text-[18px] font-semibold tracking-tight">
            <span>SOS</span>
            <span className="font-medium text-muted">ora</span>
          </p>
          <p className="mt-2 text-[13px] text-muted">{error ?? "Loading the Swannanoa road graph"}</p>
          {error ? (
            <button type="button" onClick={() => refresh()} className="mt-4 h-8 rounded-md bg-accent px-3 text-[13px]">
              Retry
            </button>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-bg text-ink">
      <Header state={state} mapPhase={mapPhase} playing={playing} busy={busy} onRun={() => void run()} />
      {error ? <p className="shrink-0 bg-critical/15 px-4 py-1 text-[12px] text-critical">{error}</p> : null}
      <div className="relative flex min-h-0 flex-1">
        {railOpen ? (
          <IncidentSidebar
            incidents={incidents}
            selectedId={selectedId}
            busy={busy}
            reviewStatus={state.review.status}
            placeMode={placeMode}
            draftPoint={draftPoint}
            onSelect={selectIncident}
            onCollapse={() => setRailOpen(false)}
            onPlace={setPlaceMode}
            onCreate={async ({ message, people, point }) => {
              const created = await createIncident({
                client_id: `ui-${crypto.randomUUID()}`,
                source_id: "dashboard",
                lon: point[0],
                lat: point[1],
                message,
                people_affected: people,
              });
              setPlaceMode(false);
              setDraftPoint(null);
              const incident = created && typeof created === "object" && "incident" in created ? created.incident : null;
              if (incident && typeof incident === "object" && "id" in incident && typeof incident.id === "string") {
                selectIncident(incident.id);
              }
            }}
          />
        ) : (
          <button
            type="button"
            aria-label="Show incidents"
            onClick={() => setRailOpen(true)}
            className="grid w-10 shrink-0 place-items-center border-r border-line bg-surface text-muted hover:text-ink"
          >
            <PanelLeftOpen size={16} />
          </button>
        )}

        <section className="relative min-w-0 flex-1">
          <RescueMap
            state={state}
            roads={roads}
            incidents={incidents}
            selectedId={selectedId}
            basemap={basemap}
            imageryTiles={imageryTiles}
            imageryLabel={imageryLabel}
            focusRoute={focusRoute}
            focusToken={focusToken}
            placeMode={placeMode}
            draftPoint={draftPoint}
            onBasemap={(mode) => {
              setBasemap(mode);
              if (mode === "street") {
                setImageryTiles(null);
                setImageryLabel(null);
              }
            }}
            onClearImagery={() => {
              setImageryTiles(null);
              setImageryLabel(null);
              setBasemap("street");
            }}
            onSelect={selectIncident}
            onMapClick={(point) => {
              if (placeMode) setDraftPoint(point);
            }}
            onPhase={setMapPhase}
          />
          {roadsError ? (
            <p className="pointer-events-none absolute bottom-16 left-3 z-10 max-w-sm text-[12px] text-warning">{roadsError}</p>
          ) : null}
          {toast ? (
            <div
              className={`pointer-events-none absolute inset-x-0 z-20 flex justify-center px-4 ${timelineOpen ? "bottom-52" : "bottom-[4.75rem]"}`}
            >
              <p className="max-w-md rounded-md border border-line bg-surface/95 px-3 py-2 text-center text-[13px] leading-5 text-ink">{toast}</p>
            </div>
          ) : null}
          <ScenarioDock
            step={step}
            playing={playing}
            busy={busy}
            events={state.events}
            timelineOpen={timelineOpen}
            canPrev={prevTarget(step) != null}
            canNext={nextTarget(step) != null}
            onPrev={() => {
              const target = prevTarget(step);
              if (target != null) void goto(target);
            }}
            onNext={() => {
              const target = nextTarget(step);
              if (target != null) void goto(target);
            }}
            onTogglePlay={() => setPlaying((value) => !value)}
            onReset={() => {
              setPlaying(false);
              void reset();
            }}
            onToggleTimeline={() => setTimelineOpen((value) => !value)}
          />
        </section>

        {intelOpen ? (
          <div className={narrow ? "absolute inset-y-0 right-0 z-30" : "contents"}>
            <IntelPanel
              state={state}
              incident={selected}
              route={focusRoute}
              routeError={routeError}
              busy={busy}
              onClose={() => setIntelOpen(false)}
              onAcknowledge={() => void acknowledge()}
              onShowImagery={(which) => {
                const layer = state.imagery[which];
                setImageryTiles(layer.tiles);
                setImageryLabel(`${layer.label} · ${layer.release_date}`);
                setBasemap("satellite");
              }}
            />
          </div>
        ) : null}
      </div>
    </main>
  );
}

function stageNote(state: AppState): string | null {
  const index = stageIndex(state.scenario.step);
  if (state.scenario.step === 5 && index === 1) {
    const name = state.system.closure_name ?? "The selected segment";
    return `${name} is marked closed in this simulation. Any candidate that uses it is withdrawn.`;
  }
  if (state.scenario.step === 6) {
    return state.routes.status === "unreachable"
      ? "No replacement path is in the road graph. The objective is potentially isolated."
      : "A replacement path was calculated on the remaining graph. It is not a safety clearance.";
  }
  if (state.scenario.step === 9) {
    const id = state.incidents[0]?.id;
    return id ? `${id} is stored. Review is requested. Nothing is dispatched.` : "Review is requested. Nothing is dispatched.";
  }
  return null;
}

