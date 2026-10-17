export type LngLat = [number, number];

export type RoutePath = {
  length_m: number;
  edge_ids: string[];
  edge_count: number;
  geometry: LngLat[];
  roads: string[];
  origin_snap_m: number;
  destination_snap_m: number;
};

export type Incident = {
  id: string;
  client_id: string;
  source_id: string;
  lon: number;
  lat: number;
  message: string;
  people_affected: number | null;
  medical: string | null;
  mobility: string | null;
  urgency: "critical" | "watch";
  delivery_status: string;
  verification: string;
  created_at: string;
};

export type QueueIncident = {
  id: string;
  client_id: string;
  source: "backend" | "fixture";
  provenance: string;
  lon: number | null;
  lat: number | null;
  title: string;
  location: string;
  locationNote?: string;
  message: string;
  people_affected: number | null;
  medical: string | null;
  mobility: string | null;
  urgency: "critical" | "high" | "watch";
  delivery_status: string;
  verification: string;
  created_at: string;
  map_ready: boolean;
  map_note?: string;
};

export type CalculatedRoute = {
  status: "ok" | "unreachable" | "snap_failed";
  length_m: number | null;
  edge_ids: string[];
  edge_count: number;
  geometry: LngLat[];
  roads: string[];
  origin_snap_m: number;
  destination_snap_m: number;
};

export type BasemapMode = "street" | "satellite" | "hybrid";

export type MapPhase = "loading" | "ready" | "error";

export type Detection = {
  id: string;
  class: string;
  confidence: number | null;
  confidence_note?: string;
  geometry: { type: string; coordinates: number[][][] } | null;
  road_segment_ids: string[];
  review_status: string;
  inference_mode: string;
  model_version: string | null;
  image_id: string;
  map_ready: boolean;
  map_note?: string | null;
};

export type Closure = {
  id: string;
  name: string;
  highway: string;
  geometry: LngLat[];
  source: string;
};

export type ScenarioEvent = {
  id: number;
  at: string;
  kind: string;
  step: number;
  message: string;
};

export type ImageryLayer = {
  label: string;
  release_date: string;
  release: string;
  tiles: string[];
  attribution: string;
};

export type AppState = {
  revision: number;
  scenario: {
    id: string;
    name: string;
    step: number;
    step_count: number;
    step_id: string;
    step_label: string;
    step_title: string;
    next_title: string | null;
    mode: string;
    clock: string;
  };
  steps: { id: string; label: string; title: string; index: number }[];
  rescue_unit: { id: string; name: string; lon: number; lat: number; fictional: boolean };
  objective: { lon: number; lat: number; label: string };
  incidents: Incident[];
  closures: Closure[];
  detections: Detection[];
  routes: {
    status: "none" | "proposed" | "invalidated" | "rerouted" | "unreachable";
    conflicts: boolean;
    active: RoutePath | null;
    invalidated: RoutePath | null;
    alternate: RoutePath | null;
  };
  events: ScenarioEvent[];
  explanation: {
    inference_mode: string;
    provider?: string;
    model?: string | null;
    summary?: string;
    access?: string;
    uncertainties?: string[];
    human_review?: boolean;
  } | null;
  review: { status: "not_requested" | "requested" | "acknowledged"; note: string };
  ml: { mode: string; detail: string };
  imagery: {
    selected: boolean;
    before: ImageryLayer;
    after: ImageryLayer;
    alignment_note: string;
  };
  system: {
    graph_nodes: number;
    graph_edges: number;
    region: string;
    graph_note: string;
    demo_mode: boolean;
    closure_name: string | null;
    disclaimer: string;
  };
};

export type FeatureCollection = {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    properties: Record<string, string | number | boolean | null>;
    geometry: { type: string; coordinates: unknown };
  }[];
};
