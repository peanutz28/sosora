"use client";

import { useEffect, useRef, useState } from "react";
import type { GeoJSONSource, Map as MlMap } from "maplibre-gl";
import { Layers, LocateFixed, Maximize2, Minus, Plus } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";
import { loadHybridStyle, SATELLITE_TILES, satelliteStyle, STREET_STYLE } from "@/components/map/mapStyle";
import type { AppState, BasemapMode, CalculatedRoute, FeatureCollection, LngLat, MapPhase, QueueIncident } from "@/lib/types";

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

const ASHVILLE: LngLat = [-82.5515, 35.5951];

type Props = {
  state: AppState;
  roads: FeatureCollection | null;
  incidents: QueueIncident[];
  selectedId: string | null;
  basemap: BasemapMode;
  imageryTiles: string[] | null;
  imageryLabel: string | null;
  focusRoute: CalculatedRoute | null;
  focusToken: number;
  placeMode: boolean;
  draftPoint: LngLat | null;
  onBasemap: (mode: BasemapMode) => void;
  onClearImagery: () => void;
  onSelect: (id: string) => void;
  onMapClick: (point: LngLat) => void;
  onPhase: (phase: MapPhase, detail?: string) => void;
};

export function RescueMap({
  state,
  roads,
  incidents,
  selectedId,
  basemap,
  imageryTiles,
  imageryLabel,
  focusRoute,
  focusToken,
  placeMode,
  draftPoint,
  onBasemap,
  onClearImagery,
  onSelect,
  onMapClick,
  onPhase,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const nodeRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const appliedRef = useRef("");
  const lastFit = useRef<number | null>(null);
  const onSelectRef = useRef(onSelect);
  const onClickRef = useRef(onMapClick);
  const onPhaseRef = useRef(onPhase);
  const onBasemapRef = useRef(onBasemap);
  const incidentsRef = useRef(incidents);
  const basemapRef = useRef(basemap);
  const styleToken = useRef(0);
  const satelliteFallbackRef = useRef(false);
  const [epoch, setEpoch] = useState(0);
  const [phase, setPhase] = useState<MapPhase>("loading");
  const [detail, setDetail] = useState<string | null>(null);
  const [imageryNote, setImageryNote] = useState<string | null>(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [overlays, setOverlays] = useState({
    routes: true,
    closures: true,
    damage: true,
    roads: false,
  });

  onSelectRef.current = onSelect;
  onClickRef.current = onMapClick;
  onPhaseRef.current = onPhase;
  onBasemapRef.current = onBasemap;
  incidentsRef.current = incidents;
  basemapRef.current = basemap;

  useEffect(() => {
    const node = nodeRef.current;
    if (!node) return;
    let map: MlMap | null = null;
    let cancelled = false;

    (async () => {
      try {
        const maplibregl = (await import("maplibre-gl")).default;
        await import("maplibre-gl/dist/maplibre-gl.css");
        if (cancelled || !nodeRef.current) return;
        map = new maplibregl.Map({
          container: nodeRef.current,
          style: STREET_STYLE,
          center: ASHVILLE,
          zoom: 11.15,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        (window as unknown as { __sosMap?: MlMap }).__sosMap = map;
        appliedRef.current = "street";
        const markReady = () => {
          if (cancelled || !map || !map.isStyleLoaded()) return;
          if (!addLayers(map)) return;
          map.resize();
          setEpoch((value) => value + 1);
          setPhase("ready");
          setDetail(null);
          onPhaseRef.current("ready");
        };
        map.on("load", markReady);
        map.on("style.load", markReady);
        map.on("error", (event) => {
          const sourceId = "sourceId" in event ? String(event.sourceId ?? "") : "";
          const message = event.error?.message ?? "Map request failed.";
          if (sourceId === "imagery" || sourceId === "sos-satellite") {
            setImageryNote("Satellite imagery is unavailable. Showing the street map.");
            if (basemapRef.current === "satellite" && !satelliteFallbackRef.current && map) {
              satelliteFallbackRef.current = true;
              styleToken.current += 1;
              appliedRef.current = "street";
              onBasemapRef.current("street");
              map.setStyle(STREET_STYLE);
            }
            return;
          }
          if (!sourceId && /failed to fetch|ajaxerror|style|webgl/i.test(message)) {
            setPhase("error");
            setDetail(message);
            onPhaseRef.current("error", message);
          }
        });
        map.on("click", (event) => {
          onClickRef.current([event.lngLat.lng, event.lngLat.lat]);
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "WebGL map failed to start.";
        setPhase("error");
        setDetail(message);
        onPhaseRef.current("error", message);
      }
    })();

    const observer = new ResizeObserver(() => mapRef.current?.resize());
    observer.observe(node);
    const slow = window.setTimeout(() => {
      setPhase((current) => {
        if (current !== "loading") return current;
        onPhaseRef.current("error", "The street style did not finish loading.");
        return "error";
      });
      setDetail((current) => current ?? "The street style did not finish loading.");
    }, 12000);

    return () => {
      cancelled = true;
      window.clearTimeout(slow);
      observer.disconnect();
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    const tiles = imageryTiles?.length ? imageryTiles : [SATELLITE_TILES];
    const key = basemap === "street" ? "street" : `${basemap}:${tiles.join("|")}`;
    if (appliedRef.current === key) return;
    const token = ++styleToken.current;
    satelliteFallbackRef.current = false;
    setImageryNote(null);

    (async () => {
      if (basemap === "hybrid") {
        const hybrid = await loadHybridStyle(tiles);
        if (token !== styleToken.current) return;
        if (!hybrid) {
          appliedRef.current = "street";
          setImageryNote("Satellite imagery is unavailable. Showing the street map.");
          onBasemapRef.current("street");
          map.setStyle(STREET_STYLE);
          return;
        }
        appliedRef.current = key;
        map.setStyle(hybrid);
        return;
      }
      if (token !== styleToken.current) return;
      appliedRef.current = key;
      map.setStyle(basemap === "street" ? STREET_STYLE : satelliteStyle(tiles));
    })();

    return () => {
      styleToken.current += 1;
    };
  }, [basemap, epoch, imageryTiles]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("sos-roads")) return;
    const active = state.routes.status === "proposed" || state.routes.status === "rerouted" ? state.routes.active : null;
    setData(map, "sos-roads", overlays.roads && roads ? roads : EMPTY);
    setData(map, "sos-damage", polygons(state));
    setData(map, "sos-closures", lines(state.closures.map((item) => item.geometry)));
    setData(map, "sos-old", line(state.routes.invalidated?.geometry));
    setData(map, "sos-alt", line(state.routes.alternate?.geometry));
    setData(map, "sos-active", line(active?.geometry));
    const focus = focusRoute?.status === "ok" ? focusRoute.geometry : undefined;
    setData(map, "sos-focus", line(focus));
    if (map.getLayer("sos-active")) {
      map.setPaintProperty("sos-active", "line-color", state.routes.conflicts ? "#C4924A" : "#3C9B6E");
    }
    const show = (ids: string[], visible: boolean) => {
      for (const id of ids) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    };
    show(["sos-roads"], overlays.roads);
    show(["sos-damage-fill", "sos-damage-line"], overlays.damage);
    show(["sos-old", "sos-alt", "sos-active-case", "sos-active", "sos-focus-case", "sos-focus"], overlays.routes);
    show(["sos-closure"], overlays.closures);
  }, [epoch, focusRoute, overlays, roads, state]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0 || !map.getSource("sos-active")) return;
    if (lastFit.current === state.scenario.step) return;
    lastFit.current = state.scenario.step;
    fit(map, state, incidentsRef.current, focusRoute);
  }, [epoch, focusRoute, state]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    let cancelled = false;
    const markers: { remove: () => void }[] = [];
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (cancelled || !mapRef.current) return;
      const place = (element: HTMLElement, lon: number, lat: number) => {
        const marker = new maplibregl.Marker({ element, anchor: "center" }).setLngLat([lon, lat]).addTo(map);
        markers.push(marker);
      };
      const rescue = document.createElement("div");
      rescue.className = "pin pin-rescue";
      rescue.title = `${state.rescue_unit.name}. Fictional unit.`;
      place(rescue, state.rescue_unit.lon, state.rescue_unit.lat);

      const objective = document.createElement("div");
      objective.className = "pin pin-objective";
      objective.title = state.objective.label;
      place(objective, state.objective.lon, state.objective.lat);

      for (const incident of incidents) {
        if (!incident.map_ready || incident.lon == null || incident.lat == null) continue;
        const wrap = document.createElement("div");
        wrap.className = "pin-wrap";
        const button = document.createElement("button");
        button.type = "button";
        button.className = `pin pin-sos pin-${incident.urgency}${incident.id === selectedId ? " is-selected" : ""}`;
        button.title = `${incident.id}. ${incident.title}`;
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectRef.current(incident.id);
        });
        wrap.appendChild(button);
        if (incident.id === selectedId) {
          const label = document.createElement("span");
          label.className = "pin-label";
          label.textContent = incident.id;
          wrap.appendChild(label);
        }
        place(wrap, incident.lon, incident.lat);
      }

      if (draftPoint) {
        const draft = document.createElement("div");
        draft.className = "pin pin-draft";
        draft.title = "New report location";
        place(draft, draftPoint[0], draftPoint[1]);
      }
    })();
    return () => {
      cancelled = true;
      markers.forEach((marker) => marker.remove());
    };
  }, [draftPoint, epoch, incidents, selectedId, state.objective, state.rescue_unit]);

  useEffect(() => {
    if (!selectedId) return;
    const incident = incidentsRef.current.find((item) => item.id === selectedId);
    const map = mapRef.current;
    if (!incident || incident.lon == null || incident.lat == null || !map) return;
    map.flyTo({
      center: [incident.lon, incident.lat],
      zoom: Math.max(map.getZoom(), 13),
      duration: 700,
      essential: true,
    });
  }, [focusToken, selectedId]);

  const retryStreet = () => {
    const map = mapRef.current;
    if (!map) return;
    appliedRef.current = "street";
    setPhase("loading");
    setDetail(null);
    onBasemap("street");
    map.setStyle(STREET_STYLE);
  };

  const isolated = state.routes.status === "unreachable" && state.scenario.step >= 6;

  return (
    <div ref={wrapRef} className={`absolute inset-0 bg-bg ${placeMode ? "cursor-crosshair" : ""}`}>
      <div ref={nodeRef} className="absolute inset-0 h-full w-full" />

      {phase !== "ready" ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-bg/90">
          <div className="max-w-sm px-6 text-center">
            <p className="text-[15px] text-ink">{phase === "error" ? "The map style did not load." : "Loading the map"}</p>
            <p className="mt-1 text-[13px] leading-5 text-muted">
              {detail ?? "Streets for Asheville and Swannanoa are loading from OpenFreeMap."}
            </p>
            {phase === "error" ? (
              <button type="button" onClick={retryStreet} className="mt-4 h-8 rounded-md bg-accent px-3 text-[13px] text-ink">
                Retry street map
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="absolute top-3 left-3 z-10 flex max-w-[calc(100%-8rem)] flex-col items-start gap-2">
        <div className="flex overflow-hidden rounded-md border border-line bg-surface/95">
          {(["street", "satellite", "hybrid"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onBasemap(mode)}
              className={`h-8 px-2.5 text-[12px] capitalize ${basemap === mode ? "bg-elevated text-ink" : "text-muted"}`}
            >
              {mode}
            </button>
          ))}
        </div>
        <div className="pointer-events-none flex flex-wrap gap-x-3 gap-y-1 rounded-md bg-surface/80 px-2 py-1 text-[11px] text-muted">
          <Key color="#3C9B6E" label="Candidate" />
          <Key color="#C46B64" label="Closed or withdrawn" />
          <Key color="#C4924A" label="Suspected" />
          <Key color="#8FBFB6" label="Selected access" />
        </div>
        {imageryLabel ? (
          <button type="button" onClick={onClearImagery} className="rounded-md bg-surface/95 px-2 py-1 text-left text-[12px] text-muted">
            {imageryLabel}
            <span className="ml-2 text-ink">Clear</span>
          </button>
        ) : null}
        {imageryNote ? <p className="max-w-xs rounded-md bg-surface/95 px-2 py-1 text-[12px] text-warning">{imageryNote}</p> : null}
        {isolated ? (
          <div className="max-w-xs rounded-md border border-critical/40 bg-surface/95 px-3 py-2">
            <p className="text-[13px] text-critical">Potentially isolated</p>
            <p className="text-[12px] leading-5 text-muted">No path remains in the loaded road graph.</p>
          </div>
        ) : null}
      </div>

      <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
        <div className="flex flex-col overflow-hidden rounded-md border border-line bg-surface/95">
          <IconButton label="Zoom in" onClick={() => mapRef.current?.zoomIn()} icon={<Plus size={15} />} />
          <IconButton label="Zoom out" onClick={() => mapRef.current?.zoomOut()} icon={<Minus size={15} />} />
        </div>
        <div className="flex flex-col overflow-hidden rounded-md border border-line bg-surface/95">
          <IconButton label="Fit corridor" onClick={() => mapRef.current && fit(mapRef.current, state, incidents, focusRoute)} icon={<LocateFixed size={15} />} />
          <IconButton label="Layers" onClick={() => setLayersOpen((open) => !open)} icon={<Layers size={15} />} />
          <IconButton
            label="Fullscreen map"
            onClick={() => {
              if (document.fullscreenElement) document.exitFullscreen();
              else wrapRef.current?.requestFullscreen();
            }}
            icon={<Maximize2 size={15} />}
          />
        </div>
        {layersOpen ? (
          <div className="w-44 rounded-md border border-line bg-surface p-2 text-[12px]">
            <LayerToggle label="Routes" on={overlays.routes} onClick={() => setOverlays((prev) => ({ ...prev, routes: !prev.routes }))} />
            <LayerToggle label="Closures" on={overlays.closures} onClick={() => setOverlays((prev) => ({ ...prev, closures: !prev.closures }))} />
            <LayerToggle label="Suspected damage" on={overlays.damage} onClick={() => setOverlays((prev) => ({ ...prev, damage: !prev.damage }))} />
            <LayerToggle label="Road graph" on={overlays.roads} onClick={() => setOverlays((prev) => ({ ...prev, roads: !prev.roads }))} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function IconButton({ label, onClick, icon }: { label: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick} className="grid h-8 w-8 place-items-center text-muted hover:text-ink">
      {icon}
    </button>
  );
}

function LayerToggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="flex w-full items-center justify-between rounded px-1.5 py-1.5 text-left hover:bg-elevated">
      <span>{label}</span>
      <span className={`h-1.5 w-1.5 rounded-full ${on ? "bg-accent-soft" : "bg-faint/50"}`} />
    </button>
  );
}

function Key({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className="inline-block h-0.5 w-3 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function addLayers(map: MlMap): boolean {
  if (map.getSource("sos-roads")) return false;
  const addSource = (id: string) => map.addSource(id, { type: "geojson", data: EMPTY as never });
  addSource("sos-roads");
  addSource("sos-damage");
  addSource("sos-closures");
  addSource("sos-old");
  addSource("sos-alt");
  addSource("sos-active");
  addSource("sos-focus");
  map.addLayer({
    id: "sos-roads",
    type: "line",
    source: "sos-roads",
    paint: {
      "line-color": "#D5DEE8",
      "line-opacity": 0.35,
      "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.4, 14, 1.6],
    },
  });
  map.addLayer({ id: "sos-damage-fill", type: "fill", source: "sos-damage", paint: { "fill-color": "#C4924A", "fill-opacity": 0.22 } });
  map.addLayer({ id: "sos-damage-line", type: "line", source: "sos-damage", paint: { "line-color": "#C4924A", "line-width": 1.25 } });
  map.addLayer({
    id: "sos-old",
    type: "line",
    source: "sos-old",
    paint: { "line-color": "#C46B64", "line-width": 3, "line-dasharray": [1.4, 1.2], "line-opacity": 0.9 },
  });
  map.addLayer({
    id: "sos-alt",
    type: "line",
    source: "sos-alt",
    paint: { "line-color": "#8FBFB6", "line-width": 2, "line-dasharray": [2, 1.5], "line-opacity": 0.8 },
  });
  map.addLayer({ id: "sos-closure", type: "line", source: "sos-closures", paint: { "line-color": "#C46B64", "line-width": 5, "line-opacity": 0.95 } });
  map.addLayer({ id: "sos-active-case", type: "line", source: "sos-active", paint: { "line-color": "#07140F", "line-width": 7, "line-opacity": 0.55 } });
  map.addLayer({ id: "sos-active", type: "line", source: "sos-active", paint: { "line-color": "#3C9B6E", "line-width": 3.5 } });
  map.addLayer({ id: "sos-focus-case", type: "line", source: "sos-focus", paint: { "line-color": "#101820", "line-width": 6, "line-opacity": 0.45 } });
  map.addLayer({
    id: "sos-focus",
    type: "line",
    source: "sos-focus",
    paint: { "line-color": "#8FBFB6", "line-width": 2.5, "line-dasharray": [1.2, 0.8] },
  });
  return true;
}

function setData(map: MlMap, id: string, data: FeatureCollection) {
  const source = map.getSource(id) as GeoJSONSource | undefined;
  source?.setData(data as never);
}

function fit(map: MlMap, state: AppState, incidents: QueueIncident[], focusRoute: CalculatedRoute | null) {
  const points: LngLat[] = [
    [state.rescue_unit.lon, state.rescue_unit.lat],
    [state.objective.lon, state.objective.lat],
  ];
  for (const incident of incidents) {
    if (incident.map_ready && incident.lon != null && incident.lat != null) points.push([incident.lon, incident.lat]);
  }
  const routes = [state.routes.active, state.routes.invalidated, focusRoute?.status === "ok" ? focusRoute : null];
  for (const route of routes) {
    if (route?.geometry?.length) points.push(...route.geometry);
  }
  if (points.length < 2) {
    map.easeTo({ center: ASHVILLE, zoom: 11.15, duration: 600 });
    return;
  }
  let west = points[0][0];
  let east = points[0][0];
  let south = points[0][1];
  let north = points[0][1];
  for (const [lon, lat] of points) {
    west = Math.min(west, lon);
    east = Math.max(east, lon);
    south = Math.min(south, lat);
    north = Math.max(north, lat);
  }
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    { padding: { top: 64, bottom: 96, left: 48, right: 56 }, duration: 800, maxZoom: 14.5 },
  );
}

function line(coords: LngLat[] | undefined): FeatureCollection {
  if (!coords || coords.length < 2) return EMPTY;
  return {
    type: "FeatureCollection",
    features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } }],
  };
}

function lines(groups: LngLat[][]): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: groups
      .filter((coords) => coords.length >= 2)
      .map((coords) => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } })),
  };
}

function polygons(state: AppState): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: state.detections
      .filter((item) => item.map_ready && item.geometry)
      .map((item) => ({
        type: "Feature" as const,
        properties: { id: item.id },
        geometry: item.geometry as { type: string; coordinates: unknown },
      })),
  };
}
