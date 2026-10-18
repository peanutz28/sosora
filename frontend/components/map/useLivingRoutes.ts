import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import type { GeoJSONSource, Map as MlMap } from "maplibre-gl";
import type { CalculatedRoute, Closure, FeatureCollection, LngLat, QueueIncident } from "@/lib/types";

const collection = (routes: LngLat[][]): FeatureCollection => ({ type: "FeatureCollection", features: routes.filter(r => r.length > 1).map(coordinates => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates } })) });
const physical = (id: string) => id.replace(/:(f|b)$/, "");

/** Project the closure onto the last known route, keeping the base side only. */
export function routeStub(route: CalculatedRoute, closures: Closure[]): LngLat[] {
  const blocked = closures.find(c => route.edge_ids.some(id => physical(id) === physical(c.id)));
  if (!blocked || route.geometry.length < 2) return [];
  const target = blocked.geometry[Math.floor(blocked.geometry.length / 2)];
  if (!target) return [];
  let closest = Infinity, index = 0, end: LngLat = route.geometry[0];
  const scale = Math.cos(target[1] * Math.PI / 180);
  for (let i = 0; i < route.geometry.length - 1; i++) {
    const a = route.geometry[i], b = route.geometry[i + 1];
    const dx = (b[0] - a[0]) * scale, dy = b[1] - a[1];
    const t = Math.max(0, Math.min(1, (((target[0] - a[0]) * scale * dx) + (target[1] - a[1]) * dy) / (dx * dx + dy * dy || 1)));
    const p: LngLat = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
    const distance = ((target[0] - p[0]) * scale) ** 2 + (target[1] - p[1]) ** 2;
    if (distance < closest) { closest = distance; index = i; end = p; }
  }
  return [...route.geometry.slice(0, index + 1), end];
}

export function useLivingRoutes(mapRef: RefObject<MlMap | null>, epoch: number, incidents: QueueIncident[], closures: Closure[], visible: boolean) {
  const previous = useRef(new Map<string, CalculatedRoute>());
  const flashUntil = useRef(0);
  const closureKey = useRef("");
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    for (const id of ["sos-living", "sos-broken", "sos-route-flash"]) {
      if (!map.getSource(id)) map.addSource(id, { type: "geojson", data: collection([]) as never });
    }
    const layer = (id: string, source: string, color: string, width: number, blur = 0, opacity = 1, dash?: number[]) => {
      if (!map.getLayer(id)) map.addLayer({ id, type: "line", source, layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": color, "line-width": width, "line-blur": blur, "line-opacity": opacity, ...(dash ? { "line-dasharray": dash } : {}) } });
    };
    layer("sos-living-glow", "sos-living", "#3ee0cf", 10, 5, .22);
    layer("sos-living", "sos-living", "#3ee0cf", 2.5, 0, .95, [0, 2, 3]);
    layer("sos-broken", "sos-broken", "#FF3B30", 2.5, 0, .55, [1, 2]);
    layer("sos-route-flash", "sos-route-flash", "#FF3B30", 4);
    const key = closures.map(c => c.id).sort().join("|");
    const changed = key !== closureKey.current;
    const flashes: LngLat[][] = [], live: LngLat[][] = [], broken: LngLat[][] = [];
    for (const incident of incidents) {
      const old = previous.current.get(incident.id);
      if (changed && old && closures.some(c => old.edge_ids.some(id => physical(id) === physical(c.id)))) flashes.push(old.geometry);
      if (incident.reachable === true && incident.route?.status === "ok") {
        live.push(incident.route.geometry);
        previous.current.set(incident.id, incident.route);
      } else if (incident.reachable === false && incident.route?.status !== "snap_failed" && old) {
        broken.push(routeStub(old, closures));
      }
    }
    for (const id of previous.current.keys()) if (!incidents.some(i => i.id === id)) previous.current.delete(id);
    const data = (id: string, values: LngLat[][]) => (map.getSource(id) as GeoJSONSource).setData(collection(values) as never);
    data("sos-living", live); data("sos-broken", broken);
    if (changed) {
      data("sos-route-flash", flashes);
      flashUntil.current = performance.now() + 3200;
      closureKey.current = key;
    }
    for (const id of ["sos-living-glow", "sos-living", "sos-broken", "sos-route-flash"]) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  }, [mapRef, epoch, incidents, closures, visible]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch || !visible) return;
    let frame = 0, last = 0;
    const dashes = [[0, 2, 3], [.5, 2, 2.5], [1, 2, 2], [1.5, 2, 1.5], [2, 2, 1], [2.5, 2, .5], [3, 2, 0]];
    const tick = (now: number) => {
      if (now - last > 48 && !document.hidden) {
        last = now;
        if (map.getLayer("sos-living")) map.setPaintProperty("sos-living", "line-dasharray", dashes[Math.floor(now / 95) % dashes.length]);
        if (map.getLayer("sos-route-flash")) {
          const remaining = flashUntil.current - now;
          map.setPaintProperty("sos-route-flash", "line-opacity", remaining > 0 ? Math.min(1, remaining / 500) * (.55 + .45 * Math.sin(now / 65)) : 0);
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [mapRef, epoch, visible]);
}
