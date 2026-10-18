import { useEffect } from "react";
import type { RefObject } from "react";
import type { Map as MlMap } from "maplibre-gl";

/** Drop displacement before any other effect when sustained frame times miss budget. */
export function useTerrainBudget(mapRef: RefObject<MlMap | null>, epoch: number) {
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !epoch) return;
    let frame = 0, last = 0, elapsed = 0, samples = 0;
    const start = performance.now();
    const tick = (now: number) => {
      if (!document.hidden && now - start > 4000) {
        if (last && now - last < 1000) { elapsed += now - last; samples++; }
        if (samples >= 90 || elapsed > 3000) {
          const fps = Math.round(1000 * samples / elapsed);
          map.getCanvas().dataset.frameRate = String(fps);
          if (fps < 55 && map.getTerrain()) {
            map.setTerrain(null);
            map.getCanvas().dataset.terrainFallback = "true";
          }
          elapsed = 0; samples = 0;
        }
        last = now;
      } else last = 0;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [mapRef, epoch]);
}
