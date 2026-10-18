import { useEffect, useMemo } from "react";
import type { RefObject } from "react";
import type { GeoJSONSource, Map as MlMap } from "maplibre-gl";
import buffer from "@turf/buffer";
import convex from "@turf/convex";
import { featureCollection, lineString, point } from "@turf/helpers";
import type { QueueIncident } from "@/lib/types";

export function isolationZone(incidents: QueueIncident[]) {
  const points = incidents.filter(i => i.reachable === false && i.route?.status !== "snap_failed" && i.map_ready && i.lon != null && i.lat != null).map(i => point([i.lon!, i.lat!]));
  if (!points.length) return featureCollection([]);
  const hull = points.length >= 3 ? convex(featureCollection(points)) : null;
  // Collinear points and small groups still receive a valid 400 m envelope.
  const shape = hull || (points.length > 1 ? lineString(points.map(p => p.geometry.coordinates)) : points[0]);
  const buffered = buffer(shape, 400, { units: "meters", steps: 16 });
  return featureCollection(buffered ? [buffered] : []);
}

export function useIsolationZone(mapRef: RefObject<MlMap | null>, epoch: number, incidents: QueueIncident[]) {
  const key = incidents.filter(i => i.reachable === false && i.route?.status !== "snap_failed").map(i => `${i.id}:${i.lon}:${i.lat}`).sort().join("|");
  // Geometry work happens only when the isolated point set changes.
  const zone = useMemo(() => isolationZone(incidents), [key]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    if (!map.getSource("sos-isolation")) {
      map.addSource("sos-isolation", { type: "geojson", data: zone });
      const before = map.getStyle().layers.find(l => l.id.startsWith("sos-living"))?.id;
      map.addLayer({ id: "sos-isolation-fill", type: "fill", source: "sos-isolation", paint: { "fill-color": "#FF3B30", "fill-opacity": 0, "fill-opacity-transition": { duration: 600 } } }, before);
      map.addLayer({ id: "sos-isolation-edge", type: "line", source: "sos-isolation", paint: { "line-color": "#FF3B30", "line-width": 1, "line-dasharray": [4, 3], "line-opacity": 0, "line-opacity-transition": { duration: 600 } } }, before);
    }
    (map.getSource("sos-isolation") as GeoJSONSource).setData(zone);
    map.setPaintProperty("sos-isolation-fill", "fill-opacity", zone.features.length ? .12 : 0);
    map.setPaintProperty("sos-isolation-edge", "line-opacity", zone.features.length ? .8 : 0);
  }, [mapRef, epoch, zone]);
}
