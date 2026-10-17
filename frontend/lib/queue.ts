import type { AppState, Incident, QueueIncident } from "@/lib/types";

/**
 * Coordinates are midpoints of named roads in the cached OpenStreetMap extract
 * (backend/data/roads.geojson, retrieved 17 October 2026). They are not historical
 * rescue locations.
 */
const FIXTURES: QueueIncident[] = [
  {
    id: "SOS-1042",
    client_id: "fixture-sos-1042",
    source: "fixture",
    provenance: "Synthetic fixture",
    lon: -82.494781,
    lat: 35.581835,
    title: "Family stranded by flooding",
    location: "Swannanoa River Road",
    message:
      "Fictional report of a family stranded by flooding on Swannanoa River Road. This is a demo queue item, not a stored SOS and not a historical record.",
    people_affected: 4,
    medical: null,
    mobility: null,
    urgency: "critical",
    delivery_status: "simulated",
    verification: "unverified",
    created_at: "2024-09-27T16:05:00-04:00",
    map_ready: true,
  },
  {
    id: "SOS-1039",
    client_id: "fixture-sos-1039",
    source: "fixture",
    provenance: "Synthetic fixture",
    lon: -82.387545,
    lat: 35.604118,
    title: "Medical evacuation requested",
    location: "Old US Highway 70",
    locationNote: "Named Old US Highway 70 in this OpenStreetMap extract, in the Old Fort corridor.",
    message:
      "Fictional medical evacuation request on Old US Highway 70. The extract does not contain a road named Old Fort Highway, so the marker uses the named highway in that corridor.",
    people_affected: 2,
    medical: "Evacuation requested",
    mobility: null,
    urgency: "high",
    delivery_status: "simulated",
    verification: "unverified",
    created_at: "2024-09-27T16:22:00-04:00",
    map_ready: true,
  },
  {
    id: "SOS-1036",
    client_id: "fixture-sos-1036",
    source: "fixture",
    provenance: "Synthetic fixture",
    lon: null,
    lat: null,
    title: "Group isolated by rising water",
    location: "Broad River Road",
    message:
      "Fictional report of a group isolated by rising water. Broad River Road is outside the cached Swannanoa corridor graph, so no marker or route is drawn.",
    people_affected: 7,
    medical: null,
    mobility: null,
    urgency: "high",
    delivery_status: "simulated",
    verification: "unverified",
    created_at: "2024-09-27T16:48:00-04:00",
    map_ready: false,
    map_note:
      "Broad River Road is outside the OpenStreetMap extract loaded for this corridor, retrieved 17 October 2026.",
  },
];

const RANK: Record<QueueIncident["urgency"], number> = {
  critical: 0,
  high: 1,
  watch: 2,
};

function fromBackend(incident: Incident, objectiveLabel: string): QueueIncident {
  const title = incident.message.split(". ")[0] || incident.message || "Incoming SOS";
  return {
    id: incident.id,
    client_id: incident.client_id,
    source: "backend",
    provenance: "Simulated scenario",
    lon: incident.lon,
    lat: incident.lat,
    title,
    location: objectiveLabel,
    message: incident.message,
    people_affected: incident.people_affected,
    medical: incident.medical,
    mobility: incident.mobility,
    urgency: incident.urgency,
    delivery_status: incident.delivery_status,
    verification: incident.verification,
    created_at: incident.created_at,
    map_ready: true,
  };
}

export function buildQueue(state: AppState): QueueIncident[] {
  const live = state.incidents.map((incident) => fromBackend(incident, state.objective.label));
  const liveIds = new Set(live.map((item) => item.client_id));
  const fixtures = FIXTURES.filter((item) => !liveIds.has(item.client_id));
  return [...live, ...fixtures].sort((a, b) => RANK[a.urgency] - RANK[b.urgency] || a.id.localeCompare(b.id));
}
