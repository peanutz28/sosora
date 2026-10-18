import type { Map as MlMap } from "maplibre-gl";

/** Restyle the existing OpenFreeMap vector source; never replace its tiles. */
export function cinematicStyle(map: MlMap) {
  for (const layer of map.getStyle().layers) {
    if (layer.id.startsWith("sos-")) continue;
    const id = layer.id;
    // Keep the road/river hierarchy clear and avoid costly decorative buckets at hero zoom.
    if ((layer.type === "symbol" && /poi|shield|airport|one_way/.test(id)) || layer.type === "fill-extrusion" || (layer.type === "line" && /casing|hatching/.test(id))) {
      map.setLayoutProperty(id, "visibility", "none");
      continue;
    }
    if (layer.type === "background") map.setPaintProperty(id, "background-color", "#090b0e");
    if (layer.type === "raster") map.setPaintProperty(id, "raster-opacity", 0.08);
    if (layer.type === "fill") {
      map.setPaintProperty(id, "fill-color", /water/.test(id) ? "#0f3346" : "#0e1b25");
      if (/park|landcover/.test(id)) map.setPaintProperty(id, "fill-opacity", 0.18);
      if (/pattern/.test(id)) map.setPaintProperty(id, "fill-pattern", null);
    }
    if (layer.type === "line") {
      map.setPaintProperty(id, "line-color", /water/.test(id) ? "#0f3346" : /motorway|trunk|primary|secondary/.test(id) ? "#29404c" : "#1c2f3a");
      if (/park/.test(id)) map.setPaintProperty(id, "line-opacity", 0.1);
    }
    if (layer.type === "symbol" && layer.layout?.["text-field"]) {
      map.setPaintProperty(id, "text-color", "#7d95a2");
      map.setPaintProperty(id, "text-halo-color", "#090b0e");
      map.setPaintProperty(id, "text-halo-width", 1.5);
    }
  }
  if (!map.getSource("sos-elevation")) {
    map.addSource("sos-elevation", { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], tileSize: 256, encoding: "terrarium", maxzoom: 15, attribution: "Elevation © Mapzen / AWS Open Data" });
    const before = map.getStyle().layers.find(layer => layer.type === "line" || layer.type === "symbol")?.id;
    map.addLayer({ id: "sos-hillshade", type: "hillshade", source: "sos-elevation", paint: { "hillshade-shadow-color": "#05080b", "hillshade-highlight-color": "#1d3442", "hillshade-accent-color": "#0e1b25", "hillshade-exaggeration": 0.45 } }, before);
    map.setTerrain({ source: "sos-elevation", exaggeration: 1.3 });
  }
  const river = map.getStyle().layers.find(layer => layer.type === "line" && layer["source-layer"] === "waterway");
  if (river && "source" in river && !map.getLayer("sos-river-glow")) {
    // Only named Swannanoa features present in the existing vector tiles match.
    for (const [id, width, opacity, blur] of [["sos-river-glow", 14, 0.18, 7], ["sos-river-light", 1.4, 0.65, 0]] as const) {
      map.addLayer({ id, type: "line", source: river.source, "source-layer": "waterway", filter: ["any", ["==", ["get", "name"], "Swannanoa River"], ["==", ["get", "name:en"], "Swannanoa River"]], paint: { "line-color": "#22d3ee", "line-width": width, "line-opacity": opacity, "line-blur": blur } });
    }
  }
}
