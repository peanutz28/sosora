import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import type { Map as MlMap } from "maplibre-gl";
import type { Beacon, BridgeCandidate, Closure, OpsEvent } from "@/lib/types";

export function useHeroChoreography(mapRef: RefObject<MlMap | null>, epoch: number, stream: OpsEvent[], beacons: Beacon[], candidates: BridgeCandidate[], closures: Closure[], flyToken: number) {
  const seen = useRef(new Set<string>());
  const knownClosures = useRef(new Set(closures.map(c => c.id)));
  const candidateKey = useRef("");
  const [reveal, setReveal] = useState(true);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  useEffect(() => {
    timers.current.forEach(clearTimeout); timers.current = [];
    setReveal(true);
    knownClosures.current.clear(); seen.current.clear(); candidateKey.current = "";
  }, [flyToken]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch || !candidates.length) { candidateKey.current = ""; return; }
    const key = candidates.map(c => c.id).join("|");
    if (candidateKey.current === key) return;
    candidateKey.current = key;
    const xs = candidates.map(c => c.centroid[0]), ys = candidates.map(c => c.centroid[1]);
    map.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: { top: 150, bottom: 180, left: window.innerWidth > 1100 ? 390 : 50, right: window.innerWidth > 1100 ? 480 : 50 }, pitch: 50, bearing: -20, maxZoom: 15, duration: 1800 });
  }, [mapRef, epoch, candidates]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    const event = [...stream].reverse().find(e => e.kind === "radio_parsed" || (e.kind === "sensor_reading" && e.over_threshold));
    if (!event) return;
    const key = `${event.id}:${event.at}`;
    if (seen.current.has(key)) return;
    seen.current.add(key);
    const received = stream.find(e => e.kind === "radio_received" && e.radio_id === event.radio_id);
    if (event.kind === "radio_parsed" && (event.parse?.event_type !== "bridge_collapse" || received?.source_type !== "beacon")) return;
    const beacon = event.beacon_id ? beacons.find(b => b.id === event.beacon_id) : beacons.find(b => /Warren Wilson/i.test(b.name));
    if (beacon) map.flyTo({ center: [beacon.lon, beacon.lat], zoom: 15.5, pitch: 60, bearing: -20, duration: 1800 });
  }, [mapRef, epoch, stream, beacons]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    const event = [...stream].reverse().find(e => e.kind === "radio_location_confirmed");
    if (!event) return;
    const key = `${event.id}:${event.at}`;
    if (seen.current.has(key)) return;
    seen.current.add(key);
    const position = event as OpsEvent & { lon?: number; lat?: number };
    if (position.lon != null && position.lat != null) map.flyTo({ center: [position.lon, position.lat], zoom: 15.5, pitch: 60, bearing: -20, duration: 1800 });
  }, [mapRef, epoch, stream]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    const added = closures.filter(c => !knownClosures.current.has(c.id));
    knownClosures.current = new Set(closures.map(c => c.id));
    if (!added.length) { if (!closures.length) setReveal(true); return; }
    const bridge = added[0].geometry[Math.floor(added[0].geometry.length / 2)];
    if (!bridge) return;
    timers.current.forEach(clearTimeout); timers.current = [];
    setReveal(false);
    map.flyTo({ center: bridge, zoom: 15.5, pitch: 60, bearing: -20, duration: 1800 });
    timers.current.push(setTimeout(() => {
      setReveal(true);
      // Existing road shockwave and route break are revealed together at the bridge.
      timers.current.push(setTimeout(() => map.easeTo({ center: [-82.412,35.622], zoom: 12.8, pitch: 50, bearing: -20, duration: 1800 }), 650));
    }, 1800));
  }, [mapRef, epoch, closures]);
  return reveal;
}
