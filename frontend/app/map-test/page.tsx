"use client";

import { useEffect, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import { STREET_STYLE } from "@/components/map/mapStyle";

export default function MapTestPage() {
  const node = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Starting");

  useEffect(() => {
    const element = node.current;
    if (!element) return;
    let map: { remove: () => void } | null = null;
    let cancelled = false;
    (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (cancelled || !node.current) return;
      const instance = new maplibregl.Map({
        container: node.current,
        style: STREET_STYLE,
        center: [-82.5515, 35.5951],
        zoom: 11.2,
      });
      map = instance;
      instance.on("load", () => setStatus("Street tiles loaded"));
      instance.on("error", (event) => setStatus(event.error?.message ?? "Map error"));
    })();
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, []);

  return (
    <main className="h-dvh bg-bg">
      <p className="absolute top-3 left-3 z-10 rounded-md bg-surface px-2 py-1 text-[12px] text-ink">{status}</p>
      <div ref={node} className="h-full w-full" />
    </main>
  );
}
