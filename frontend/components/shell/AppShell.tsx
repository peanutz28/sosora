"use client";

import { useEffect, useMemo, useState } from "react";
import { PanelLeftOpen } from "lucide-react";
import { IncidentSidebar } from "@/components/incidents/IncidentSidebar";
import { IntelPanel } from "@/components/intel/IntelPanel";
import { RescueMap } from "@/components/map/RescueMap";
import { OpsConsole, type DrillAction } from "@/components/ops/OpsConsole";
import { agentStatus, latestAssessment, reviewCandidates } from "@/lib/ops";
import { Header } from "@/components/shell/Header";
import { useOps } from "@/hooks/useOps";
import { calculateRoute } from "@/lib/api";
import { buildQueue } from "@/lib/queue";
import type {
  BasemapMode,
  CalculatedRoute,
  LngLat,
  MapPhase,
} from "@/lib/types";

export function AppShell() {
  const {
    state,
    roads,
    beacons,
    stream,
    agentWorking,
    socketLive,
    seed,
    flyToken,
    seedDrill,
    radioAction,
    error,
    roadsError,
    busy,
    acknowledge,
    createIncident,
    refresh,
  } = useOps();
  const assessment = useMemo(() => latestAssessment(stream), [stream]);
  const candidates = useMemo(
    () => reviewCandidates(stream, assessment),
    [stream, assessment],
  );
  const radioId = [...stream]
    .reverse()
    .find((event) => event.kind === "radio_received")?.radio_id;
  const [presentation, setPresentation] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [intelOpen, setIntelOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(true);
  const [basemap, setBasemap] = useState<BasemapMode>("street");
  const [imageryTiles, setImageryTiles] = useState<string[] | null>(null);
  const [imageryLabel, setImageryLabel] = useState<string | null>(null);
  const [placeMode, setPlaceMode] = useState(false);
  const [draftPoint, setDraftPoint] = useState<LngLat | null>(null);
  const [focusRoute, setFocusRoute] = useState<CalculatedRoute | null>(null);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [mapPhase, setMapPhase] = useState<MapPhase>("loading");
  const [width, setWidth] = useState(1440);
  const [focusToken, setFocusToken] = useState(0);

  const incidents = useMemo(() => (state ? buildQueue(state) : []), [state]);
  const selected = incidents.find((item) => item.id === selectedId) ?? null;

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.repeat || event.metaKey || event.ctrlKey || event.altKey || event.key.toLowerCase() !== "p") return;
      if (event.target instanceof HTMLElement && (event.target.isContentEditable || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName))) return;
      event.preventDefault();
      setPresentation(current => !current);
      setIntelOpen(false);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

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
    if (!state || !selected || selected.lon == null || selected.lat == null) {
      setFocusRoute(null);
      setRouteError(null);
      return;
    }
    let cancel = false;
    setFocusRoute(null);
    setRouteError(null);
    calculateRoute(
      [state.rescue_unit.lon, state.rescue_unit.lat],
      [selected.lon, selected.lat],
    )
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

  const selectIncident = (id: string) => {
    setSelectedId(id);
    setIntelOpen(true);
    setFocusToken((value) => value + 1);
  };

  const act = (action: DrillAction) => {
    setSelectedId(null);
    setIntelOpen(false);
    if (action === "seed") void seedDrill();
    else void radioAction(action);
  };
  const run = async () => {
    setSelectedId(null);
    setIntelOpen(false);
    const result = await seedDrill();
    if (result) void radioAction("beacon");
  };
  const confirmBridge = (candidate: import("@/lib/types").BridgeCandidate) => {
    if (radioId) void radioAction("responder", candidate, radioId);
  };

  if (!state) {
    return (
      <main className="flex h-dvh items-center justify-center bg-bg text-ink">
        <div className="max-w-sm text-center">
          <p className="text-[18px] font-semibold tracking-tight">
            <span>SOS</span>
            <span className="font-medium text-muted">ora</span>
          </p>
          <p className="mt-2 text-[13px] text-muted">
            {error ?? "Loading the Swannanoa road graph"}
          </p>
          {error ? (
            <button
              type="button"
              onClick={() => refresh()}
              className="mt-4 h-8 rounded-md bg-accent px-3 text-[13px] font-semibold text-on-accent"
            >
              Retry
            </button>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className={`command-shell flex h-dvh flex-col overflow-hidden bg-bg text-ink ${presentation ? "presentation" : ""}`}>
      <Header
        state={state}
        mapPhase={mapPhase}
        busy={busy}
        agentState={agentStatus(agentWorking, assessment, stream)}
        onRun={() => void run()}
      />
      {error ? (
        <p className="shrink-0 bg-critical/15 px-4 py-1 text-[12px] text-critical">
          {error}
        </p>
      ) : null}
      <div className="ops-body">
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
              const incident =
                created && typeof created === "object" && "incident" in created
                  ? created.incident
                  : null;
              if (
                incident &&
                typeof incident === "object" &&
                "id" in incident &&
                typeof incident.id === "string"
              ) {
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

        <div className="ops-workspace">
          <div className="workspace-content">
            <section className="relative min-h-0 min-w-0 flex-1">
              <RescueMap
                state={state}
                stream={stream}
                beacons={beacons}
                candidates={candidates}
                onConfirmCandidate={confirmBridge}
                flyToken={flyToken}
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
                <p className="pointer-events-none absolute bottom-16 left-3 z-10 max-w-sm text-[12px] text-warning">
                  {roadsError}
                </p>
              ) : null}
            </section>

            {intelOpen && selected ? (
              <div className="detail-column">
                <IntelPanel
                  state={state}
                  incident={selected}
                  route={focusRoute}
                  routeError={routeError}
                  busy={busy}
                  onClose={() => {
                    setIntelOpen(false);
                    setSelectedId(null);
                    setFocusRoute(null);
                  }}
                  onAcknowledge={() => void acknowledge()}
                  onShowImagery={(which) => {
                    const layer = state.imagery[which];
                    setImageryTiles(layer.tiles);
                    setImageryLabel(`${layer.label} · ${layer.release_date}`);
                    setBasemap("satellite");
                  }}
                />
              </div>
            ) : (
              <OpsConsole
                state={state}
                stream={stream}
                working={agentWorking}
                socketLive={socketLive}
                seeded={!!seed}
                busy={busy}
                onAction={act}
                onConfirm={(candidate, id) => {
                  void radioAction("responder", candidate, id);
                }}
              />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
