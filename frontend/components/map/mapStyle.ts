import type { StyleSpecification } from "maplibre-gl";

export const STREET_STYLE = "https://tiles.openfreemap.org/styles/liberty";

export const SATELLITE_TILES =
  process.env.NEXT_PUBLIC_SATELLITE_TILE_URL ||
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const SATELLITE_ATTRIBUTION = "Imagery © Esri, Maxar, Earthstar Geographics";

export function satelliteStyle(tiles: string[]): StyleSpecification {
  return {
    version: 8,
    sources: {
      imagery: {
        type: "raster",
        tiles,
        tileSize: 256,
        attribution: SATELLITE_ATTRIBUTION,
      },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": "#0B1017" } },
      { id: "imagery", type: "raster", source: "imagery" },
    ],
  };
}

export async function loadHybridStyle(tiles: string[]): Promise<StyleSpecification | null> {
  try {
    const response = await fetch(STREET_STYLE);
    if (!response.ok) return null;
    const style = (await response.json()) as StyleSpecification;
    style.sources = {
      ...style.sources,
      "sos-satellite": {
        type: "raster",
        tiles,
        tileSize: 256,
        attribution: SATELLITE_ATTRIBUTION,
      },
    };
    const layers = style.layers ?? [];
    layers.unshift({ id: "sos-satellite", type: "raster", source: "sos-satellite" });
    for (const layer of layers) {
      if (layer.type === "background") {
        layer.paint = { ...(layer.paint ?? {}), "background-opacity": 0 };
      }
      if (layer.type === "fill") {
        const id = layer.id ?? "";
        if (/water|ocean|river|bay/i.test(id)) continue;
        layer.paint = { ...(layer.paint ?? {}), "fill-opacity": 0 };
      }
    }
    style.layers = layers;
    return style;
  } catch {
    return null;
  }
}
