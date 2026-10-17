"use client";

import { useEffect, useRef, useState } from "react";
import type { AppState, FeatureCollection, LngLat } from "@/lib/types";

type MapHandle = {
  resize: () => void;
  remove: () => void;
  getSource: (id: string) => { setData: (data: unknown) => void } | undefined;
  setPaintProperty: (layer: string, prop: string, value: unknown) => void;
  setLayoutProperty: (layer: string, prop: string, value: unknown) => void;
  fitBounds: (bounds: unknown, options: unknown) => void;
  on: (event: string, handler: (event?: { lngLat: { lng: number; lat: number } }) => void) => void;
  getCenter: () => { lng: number; lat: number };
  getZoom: () => number;
  getBearing: () => number;
  getPitch: () => number;
  jumpTo: (camera: unknown) => void;
  addControl: (control: unknown, position?: string) => void;
};

const empty: FeatureCollection = { type: "FeatureCollection", features: [] };

export function OpsMap({ state, roads }: { state: AppState; roads: FeatureCollection }) {
  const mainNode = useRef<HTMLDivElement>(null);
  const beforeNode = useRef<HTMLDivElement>(null);
  const mainRef = useRef<MapHandle | null>(null);
  const beforeRef = useRef<MapHandle | null>(null);
  const [ready, setReady] = useState(false);
  const [compare, setCompare] = useState(false);
  const [split, setSplit] = useState(48);
  const [hover, setHover] = useState("—");
  const [layers, setLayers] = useState({ roads: true, damage: true, routes: true, closures: true });
  const drag = useRef(false);

  useEffect(() => {
    setCompare(state.imagery.selected);
  }, [state.imagery.selected]);

  useEffect(() => {
    let dead = false;
    let main: MapHandle | null = null;
    let before: MapHandle | null = null;
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      await import("maplibre-gl/dist/maplibre-gl.css");
      if (dead || !mainNode.current || !beforeNode.current) return;
      const center: LngLat = [state.rescue_unit.lon, state.rescue_unit.lat];
      main = new maplibregl.Map({
        container: mainNode.current,
        style: style(state.imagery.after.tiles[0]),
        center,
        zoom: 12,
        attributionControl: false,
      }) as unknown as MapHandle;
      before = new maplibregl.Map({
        container: beforeNode.current,
        style: style(state.imagery.before.tiles[0]),
        center,
        zoom: 12,
        attributionControl: false,
        interactive: false,
      }) as unknown as MapHandle;
      main.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      let pending = 2;
      const loaded = () => {
        pending -= 1;
        if (pending > 0 || !main || !before) return;
        addLayers(main);
        addLayers(before);
        mainRef.current = main;
        beforeRef.current = before;
        if (!dead) setReady(true);
      };
      main.on("load", loaded);
      before.on("load", loaded);
      main.on("move", () => {
        before?.jumpTo({
          center: main?.getCenter(),
          zoom: main?.getZoom(),
          bearing: main?.getBearing(),
          pitch: main?.getPitch(),
        });
      });
      main.on("mousemove", (event) => {
        if (!event) return;
        setHover(`${event.lngLat.lat.toFixed(5)}   ${event.lngLat.lng.toFixed(5)}`);
      });
    })();
    return () => {
      dead = true;
      main?.remove();
      before?.remove();
      mainRef.current = null;
      beforeRef.current = null;
      setReady(false);
    };
    // The basemap is fixed for the life of the view.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready) return;
    paint(mainRef.current, state, roads);
    paint(beforeRef.current, state, roads);
  }, [ready, roads, state]);

  useEffect(() => {
    if (!ready) return;
    const map = mainRef.current;
    if (!map) return;
    const points: LngLat[] = [
      [state.rescue_unit.lon, state.rescue_unit.lat],
      [state.objective.lon, state.objective.lat],
    ];
    const route = state.routes.active ?? state.routes.invalidated;
    if (route) points.push(...route.geometry);
    if (points.length < 2) return;
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
      { padding: 56, duration: 800, maxZoom: 15 },
    );
    // Refit only when the scenario step changes, so polling does not yank the camera.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, state.scenario.step]);

  useEffect(() => {
    if (!ready) return;
    mainRef.current?.resize();
    beforeRef.current?.resize();
    const map = mainRef.current;
    const before = beforeRef.current;
    if (!map || !before) return;
    const show = (ids: string[], visible: boolean) => {
      for (const id of ids) {
        const value = visible ? "visible" : "none";
        map.setLayoutProperty(id, "visibility", value);
        before.setLayoutProperty(id, "visibility", value);
      }
    };
    show(["roads"], layers.roads);
    show(["damage-fill", "damage-line"], layers.damage);
    show(["old-route", "alt-route", "route-casing", "route-core"], layers.routes);
    show(["closure-casing", "closure-core", "closure-point"], layers.closures);
  }, [layers, ready, compare]);

  useEffect(() => {
    const end = () => {
      drag.current = false;
    };
    const move = (event: PointerEvent) => {
      if (!drag.current || !mainNode.current) return;
      const rect = mainNode.current.getBoundingClientRect();
      const next = ((event.clientX - rect.left) / rect.width) * 100;
      setSplit(Math.min(88, Math.max(12, next)));
    };
    window.addEventListener("pointerup", end);
    window.addEventListener("pointermove", move);
    return () => {
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointermove", move);
    };
  }, []);

  const isolated = state.routes.status === "unreachable" && state.scenario.step >= 1;

  return (
    <div className="absolute inset-0 bg-bg">
      <div ref={mainNode} className="absolute inset-0" />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ display: compare ? "block" : "none", clipPath: `inset(0 ${100 - split}% 0 0)` }}
      >
        <div ref={beforeNode} className="absolute inset-0" />
      </div>

      {compare ? (
        <button
          type="button"
          aria-label="Drag imagery divider"
          onPointerDown={() => {
            drag.current = true;
          }}
          className="absolute inset-y-0 z-20 w-6 -translate-x-1/2 cursor-col-resize"
          style={{ left: `${split}%` }}
        >
          <span className="absolute inset-y-0 left-1/2 w-px bg-info" />
          <span className="absolute top-1/2 left-1/2 h-8 w-4 -translate-x-1/2 -translate-y-1/2 border border-info bg-bg text-[9px] leading-8 text-info">
            ||
          </span>
        </button>
      ) : null}

      <div className="pointer-events-none absolute top-3 left-3 z-10 max-w-[280px]">
        <p className="text-[10px] tracking-[0.16em] text-info">SWANNANOA CORRIDOR</p>
        <p className="text-[13px] text-ink drop-shadow">{state.scenario.step_title}</p>
        {compare ? (
          <p className="mt-1 text-[10px] text-ink/90">
            Before {state.imagery.before.release_date} · After {state.imagery.after.release_date}
          </p>
        ) : null}
      </div>

      {isolated ? (
        <div className="absolute top-3 right-14 left-3 z-10 border border-critical/60 bg-bg/85 px-3 py-2 sm:left-auto sm:w-[360px]">
          <p className="text-[12px] font-semibold tracking-[0.08em] text-critical">POTENTIALLY ISOLATED</p>
          <p className="text-[12px] text-ink">No available path in the current road graph.</p>
        </div>
      ) : null}

      <Markers state={state} map={ready ? mainRef.current : null} />

      <div className="absolute bottom-3 left-3 z-10 flex max-w-[460px] flex-col gap-2">
        <div className="flex flex-wrap gap-1">
          <Chip on={layers.roads} label="Roads" onClick={() => setLayers((prev) => ({ ...prev, roads: !prev.roads }))} />
          <Chip on={layers.damage} label="Damage" onClick={() => setLayers((prev) => ({ ...prev, damage: !prev.damage }))} />
          <Chip on={layers.routes} label="Routes" onClick={() => setLayers((prev) => ({ ...prev, routes: !prev.routes }))} />
          <Chip on={layers.closures} label="Closures" onClick={() => setLayers((prev) => ({ ...prev, closures: !prev.closures }))} />
          <Chip on={compare} label="Before / after" onClick={() => setCompare((prev) => !prev)} />
        </div>
        <div className="bg-bg/75 px-2 py-1 text-[10px] leading-snug text-muted">
          <span className="mr-3 inline-flex items-center gap-1"><i className="inline-block h-1.5 w-3 bg-route" /> Candidate</span>
          <span className="mr-3 inline-flex items-center gap-1"><i className="inline-block h-1.5 w-3 bg-critical" /> Closed / withdrawn</span>
          <span className="mr-3 inline-flex items-center gap-1"><i className="inline-block h-1.5 w-3 bg-warning" /> Suspected</span>
          <span className="inline-flex items-center gap-1"><i className="inline-block h-1.5 w-3 bg-info" /> Alternate</span>
          <p className="mt-1">Roads © OpenStreetMap · Imagery © Esri Wayback · {state.system.graph_note}</p>
        </div>
      </div>

      <p className="mono pointer-events-none absolute right-3 bottom-3 z-10 bg-bg/75 px-2 py-1 text-[10px] text-muted">{hover}</p>
    </div>
  );
}

function Chip({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={`h-6 border px-2 text-[10px] tracking-[0.08em] uppercase ${on ? "border-info/60 text-info" : "border-line text-muted"} bg-bg/80`}>
      {label}
    </button>
  );
}

function Markers({ state, map }: { state: AppState; map: MapHandle | null }) {
  const bag = useRef<{ remove: () => void }[]>([]);
  useEffect(() => {
    let dead = false;
    bag.current.forEach((marker) => marker.remove());
    bag.current = [];
    if (!map) return;
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (dead) return;
      const place = (className: string, lon: number, lat: number) => {
        const element = document.createElement("div");
        element.className = className;
        const marker = new maplibregl.Marker({ element }).setLngLat([lon, lat]).addTo(map as never);
        bag.current.push(marker);
      };
      place("rescue-pin", state.rescue_unit.lon, state.rescue_unit.lat);
      if (state.incidents.length === 0) {
        place("objective-pin", state.objective.lon, state.objective.lat);
      }
      for (const incident of state.incidents) place("sos-pin", incident.lon, incident.lat);
    })();
    return () => {
      dead = true;
      bag.current.forEach((marker) => marker.remove());
      bag.current = [];
    };
  }, [map, state.incidents, state.objective.lat, state.objective.lon, state.rescue_unit.lat, state.rescue_unit.lon]);
  return null;
}

function style(tiles: string) {
  return {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {
      imagery: {
        type: "raster",
        tiles: [tiles],
        tileSize: 256,
      },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#070b10" } },
      { id: "imagery", type: "raster", source: "imagery" },
    ],
  };
}

function addLayers(map: MapHandle) {
  const source = (id: string) => {
    (map as unknown as { addSource: (name: string, spec: unknown) => void }).addSource(id, { type: "geojson", data: empty });
  };
  source("roads");
  source("damage");
  source("closures");
  source("closure-points");
  source("old");
  source("alt");
  source("active");
  const add = (map as unknown as { addLayer: (layer: unknown) => void }).addLayer.bind(map);
  add({
    id: "roads",
    type: "line",
    source: "roads",
    paint: {
      "line-color": "#d5e2ef",
      "line-width": ["interpolate", ["linear"], ["zoom"], 10, ["match", ["get", "rank"], 1, 1.4, 2, 0.8, 0.25], 15, ["match", ["get", "rank"], 1, 3.4, 2, 2.2, 1]],
      "line-opacity": ["interpolate", ["linear"], ["zoom"], 11, ["match", ["get", "rank"], 3, 0.15, 0.75], 14, 0.85],
    },
  });
  add({ id: "damage-fill", type: "fill", source: "damage", paint: { "fill-color": "#ffc14a", "fill-opacity": 0.28 } });
  add({ id: "damage-line", type: "line", source: "damage", paint: { "line-color": "#ffc14a", "line-width": 1.2 } });
  add({ id: "old-route", type: "line", source: "old", paint: { "line-color": "#ff5d5d", "line-width": 3, "line-dasharray": [1.2, 1.1], "line-opacity": 0.9 } });
  add({ id: "alt-route", type: "line", source: "alt", paint: { "line-color": "#6ad7ff", "line-width": 2, "line-dasharray": [2, 1.4], "line-opacity": 0.85 } });
  add({ id: "route-casing", type: "line", source: "active", paint: { "line-color": "#06281c", "line-width": 7 } });
  add({ id: "route-core", type: "line", source: "active", paint: { "line-color": "#3ddc97", "line-width": 3.2 } });
  add({ id: "closure-casing", type: "line", source: "closures", paint: { "line-color": "#2a0d0d", "line-width": 8 } });
  add({ id: "closure-core", type: "line", source: "closures", paint: { "line-color": "#ff5d5d", "line-width": 3.5 } });
  add({ id: "closure-point", type: "circle", source: "closure-points", paint: { "circle-radius": 6, "circle-color": "#ff5d5d", "circle-stroke-color": "#070b10", "circle-stroke-width": 2 } });
}

function paint(map: MapHandle | null, state: AppState, roads: FeatureCollection) {
  if (!map) return;
  const set = (id: string, data: unknown) => map.getSource(id)?.setData(data);
  set("roads", roads);
  set("damage", polygons(state));
  set("closures", lines(state.closures.map((item) => item.geometry)));
  set("closure-points", points(state.closures.map((item) => item.geometry)));
  set("old", line(state.routes.invalidated?.geometry));
  set("alt", line(state.routes.alternate?.geometry));
  set("active", line(state.routes.active?.geometry));
  map.setPaintProperty("route-core", "line-color", state.routes.conflicts ? "#ffc14a" : "#3ddc97");
  map.setPaintProperty("route-casing", "line-color", state.routes.conflicts ? "#2a2108" : "#06281c");
}

function line(coords: LngLat[] | undefined): FeatureCollection {
  if (!coords || coords.length < 2) return empty;
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

function points(groups: LngLat[][]): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: groups
      .filter((coords) => coords.length > 0)
      .map((coords) => ({
        type: "Feature",
        properties: {},
        geometry: { type: "Point", coordinates: coords[Math.floor(coords.length / 2)] },
      })),
  };
}

function polygons(state: AppState): FeatureCollection {
  const features = state.detections
    .filter((item) => item.map_ready && item.geometry)
    .map((item) => ({
      type: "Feature" as const,
      properties: { id: item.id },
      geometry: item.geometry as { type: string; coordinates: unknown },
    }));
  return { type: "FeatureCollection", features };
}
