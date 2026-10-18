import type { Incident } from "@/lib/types";

/** Graph access only: a path is not verified field passability. */
export function roadAccess(incident: Pick<Incident, "reachable" | "route">) {
  if (incident.route?.status === "snap_failed") {
    return { status: "unknown", label: "Access unknown", detail: "Could not locate this incident on the loaded road graph." } as const;
  }
  if (incident.reachable === false || (incident.reachable == null && incident.route?.status === "unreachable")) {
    return { status: "lost", label: "No road access", detail: "No route from a rescue base in the current road graph. Alternative access needs review." } as const;
  }
  if (incident.reachable === true || (incident.reachable == null && incident.route?.status === "ok")) {
    return { status: "available", label: "Route available", detail: "A route exists from a rescue base in the current graph. Field passability remains unverified." } as const;
  }
  return { status: "unknown", label: "Access unknown", detail: "Road access has not been calculated for this incident." } as const;
}
