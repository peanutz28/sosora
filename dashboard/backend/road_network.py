"""Swannanoa road reports and isolation analysis.

Geometry comes from the OpenStreetMap GeoJSON extract. Nothing in this module
is a hurricane closure feed. Missing reports stay "unknown", which means
unreported — not passable and not closed.

Simulated drill markings are stored by the API and returned for display, but
they do not add or remove connections. Isolation uses only operator and
resident reports, and it labels those reports as unverified or verified.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

HIGHWAY_RANK = {
    "motorway": 100,
    "motorway_link": 90,
    "trunk": 80,
    "trunk_link": 70,
    "primary": 70,
    "primary_link": 60,
    "secondary": 50,
    "secondary_link": 40,
    "tertiary": 30,
    "tertiary_link": 20,
    "unclassified": 10,
    "residential": 5,
    "living_street": 4,
    "service": 2,
    "track": 1,
}

DISCLAIMER = (
    "OpenStreetMap geometry plus demo road reports. Unknown means unreported, "
    "not safe and not closed. No hurricane closure feed is connected. "
    "Not for navigation or emergency use."
)


@dataclass(frozen=True)
class Segment:
    id: str
    u: int
    v: int
    name: str | None
    highway: str | None
    ref: str | None
    osm_bridge: bool
    length_m: float
    mid_lat: float
    mid_lng: float


@dataclass(frozen=True)
class Report:
    segment_id: str
    condition: str
    source: str
    evidence: str
    verification: str
    reported_at: str
    updated_at: str


@dataclass(frozen=True)
class Network:
    segments: dict[str, Segment]
    nodes: dict[int, tuple[float, float]]
    access_node: int
    component_count: int
    osm_bridge_count: int


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    h = sin(dp / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dl / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def parse_segment_id(raw: str) -> tuple[int, int, int]:
    text = raw.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Not an OSM edge id: {raw}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def data_class(report: Report | None) -> str:
    if report is None or report.condition == "unknown":
        return "unknown"
    if report.source == "simulation":
        return "simulated"
    if report.verification == "verified":
        return "verified"
    return "unverified_report"


def _clean_name(value: str | None) -> str | None:
    if not value:
        return None
    text = value.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    parts = []
    for part in text.split(","):
        part = part.strip()
        if part and part not in parts:
            parts.append(part)
    return " / ".join(parts) or None


def _simplify_highway(value: str | None) -> str | None:
    if not value:
        return None
    text = value.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return None
    return max(parts, key=lambda part: HIGHWAY_RANK.get(part, 0))


def _truthy_bridge(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1"}


def _polyline_length(coords: list) -> float:
    total = 0.0
    for (lng1, lat1), (lng2, lat2) in zip(coords, coords[1:]):
        total += haversine_m(lat1, lng1, lat2, lng2)
    return total


def _load_graphml(path: Path) -> dict[str, dict[str, str]]:
    root = ET.parse(path).getroot()
    ns = "{http://graphml.graphdrawing.org/xmlns}"
    keys = {node.get("id"): node.get("attr.name") for node in root.findall(f"{ns}key")}
    meta: dict[str, dict[str, str]] = {}
    for edge in root.findall(f"{ns}graph/{ns}edge"):
        sid = f"({edge.get('source')}, {edge.get('target')}, {edge.get('id')})"
        record = {}
        for item in edge.findall(f"{ns}data"):
            name = keys.get(item.get("key"))
            if name:
                record[name] = item.text or ""
        meta[sid] = record
    return meta


def choose_access_node(segments: dict[str, Segment], nodes: dict[int, tuple[float, float]]) -> int:
    """Western high-degree junction, toward Asheville and the demo rescue base.

    The mapped extract stops east of the toy rescue unit, so this is an analysis
    anchor inside the OSM graph, not a shelter or staging area.
    """
    if not nodes:
        raise ValueError("Road network has no junctions")
    lngs = [lng for _, lng in nodes.values()]
    west, east = min(lngs), max(lngs)
    cutoff = west + 0.2 * (east - west)
    degree: dict[int, int] = defaultdict(int)
    for segment in segments.values():
        degree[segment.u] += 1
        degree[segment.v] += 1
    candidates = [node_id for node_id, (_, lng) in nodes.items() if lng <= cutoff + 1e-9]
    if not candidates:
        candidates = list(nodes)
    return max(candidates, key=lambda node_id: (degree[node_id], -nodes[node_id][1], node_id))


def build_network(
    segments: dict[str, Segment],
    nodes: dict[int, tuple[float, float]],
    osm_bridge_count: int = 0,
    access_node: int | None = None,
) -> Network:
    access = access_node if access_node is not None else choose_access_node(segments, nodes)
    if access not in nodes:
        raise ValueError("Analysis entry is not in the road network")
    component_count = len(_components(set(nodes), [(seg.u, seg.v, seg.id) for seg in segments.values()]))
    return Network(
        segments=segments,
        nodes=nodes,
        access_node=access,
        component_count=component_count,
        osm_bridge_count=osm_bridge_count,
    )


def load_network(geojson_path: Path, graphml_path: Path | None = None) -> Network:
    meta = _load_graphml(graphml_path) if graphml_path and Path(graphml_path).exists() else {}
    payload = json.loads(Path(geojson_path).read_text())
    segments: dict[str, Segment] = {}
    nodes: dict[int, tuple[float, float]] = {}
    bridge_count = 0
    for feature in payload["features"]:
        sid = str(feature["id"])
        u, v, _key = parse_segment_id(sid)
        coords = feature["geometry"]["coordinates"]
        if u not in nodes:
            lng, lat = coords[0]
            nodes[u] = (lat, lng)
        if v not in nodes:
            lng, lat = coords[-1]
            nodes[v] = (lat, lng)
        info = meta.get(sid, {})
        highway = _simplify_highway(info.get("highway"))
        ref = (info.get("ref") or "").strip() or None
        osm_bridge = _truthy_bridge(info.get("bridge"))
        if osm_bridge:
            bridge_count += 1
        try:
            length = float(info["length"]) if info.get("length") else _polyline_length(coords)
        except ValueError:
            length = _polyline_length(coords)
        mid_lng, mid_lat = coords[len(coords) // 2]
        name = _clean_name(info.get("name"))
        segments[sid] = Segment(
            id=sid,
            u=u,
            v=v,
            name=name,
            highway=highway,
            ref=ref,
            osm_bridge=osm_bridge,
            length_m=length,
            mid_lat=mid_lat,
            mid_lng=mid_lng,
        )
    return build_network(segments, nodes, osm_bridge_count=bridge_count)


def catalog(network: Network) -> dict:
    access_lat, access_lng = network.nodes[network.access_node]
    return {
        "source": "OpenStreetMap",
        "condition_note": "Segment geometry does not include a passable or closed status.",
        "access": _access_payload(network, access_lat, access_lng),
        "segments": [
            {
                "id": segment.id,
                "name": segment.name,
                "highway": segment.highway,
                "ref": segment.ref,
                "osm_bridge": segment.osm_bridge,
                "length_m": round(segment.length_m, 1),
                "lat": segment.mid_lat,
                "lng": segment.mid_lng,
            }
            for segment in network.segments.values()
        ],
    }


def serialize_report(network: Network, report: Report) -> dict:
    segment = network.segments.get(report.segment_id)
    applied = report.condition in {"passable", "blocked", "damaged"} and report.source != "simulation"
    return {
        "segment_id": report.segment_id,
        "condition": report.condition,
        "source": report.source,
        "evidence": report.evidence,
        "verification": report.verification,
        "reported_at": report.reported_at,
        "updated_at": report.updated_at,
        "data_class": data_class(report),
        "applied_to_analysis": applied,
        "name": segment.name if segment else None,
        "highway": segment.highway if segment else None,
        "lat": segment.mid_lat if segment else None,
        "lng": segment.mid_lng if segment else None,
    }


def _reverse_segment_id(segment_id: str) -> str | None:
    if len(segment_id) < 5 or segment_id[0] != "(" or segment_id[-1] != ")":
        return None
    parts = [part.strip() for part in segment_id[1:-1].split(",")]
    if len(parts) != 3:
        return None
    return f"({parts[1]}, {parts[0]}, {parts[2]})"


def _inherit_opposite_blocks(network: Network, by_id: dict[str, Report], apply_simulated: bool) -> dict[str, Report]:
    """Copy a blockage onto the opposite OSM edge when that edge has no report.

    OpenStreetMap stores a two-way road as two directed edges. A click saves one
    of them. The opposite edge keeps its own report when one exists.
    """
    inherited: dict[str, Report] = {}
    for segment_id, report in by_id.items():
        if report.condition not in {"blocked", "damaged"}:
            continue
        if report.source == "simulation" and not apply_simulated:
            continue
        reverse_id = _reverse_segment_id(segment_id)
        if not reverse_id or reverse_id not in network.segments or reverse_id in by_id or reverse_id in inherited:
            continue
        inherited[reverse_id] = report
    return inherited


def analyze_network(
    network: Network,
    reports: list[Report],
    incidents: list[dict] | None = None,
    min_hinge_nodes: int = 8,
    apply_simulated: bool = False,
) -> dict:
    """Find pockets that blockage reports cut off, or that hang from one uncertain road.

    Optimistic graph: every OSM segment except real (non-simulated) blockage reports.
    Unknown segments stay in that graph, so a single blocked road in this redundant
    extract usually creates a last-link warning rather than a fully cut-off pocket.
    A pocket is fully cut off only when every exit carries a real blockage report.
    """
    incidents = incidents or []
    by_id = {report.segment_id: report for report in reports if report.segment_id in network.segments}
    nodes = set(network.nodes)
    all_edges = [(segment.u, segment.v, segment.id) for segment in network.segments.values()]
    access = network.access_node
    inherited = _inherit_opposite_blocks(network, by_id, apply_simulated)

    def real_blocked(sid: str) -> bool:
        if sid in inherited:
            return True
        report = by_id.get(sid)
        if not report or report.condition not in {"blocked", "damaged"}:
            return False
        if report.source == "simulation":
            return apply_simulated
        return True

    def real_passable(sid: str, verified_only: bool = False) -> bool:
        report = by_id.get(sid)
        if not report or report.source == "simulation" or report.condition != "passable":
            return False
        if verified_only and report.verification != "verified":
            return False
        return True

    opt_edges = [edge for edge in all_edges if not real_blocked(edge[2])]
    components = _components(nodes, opt_edges)
    access_comp = next(comp for comp in components if access in comp)
    access_set = set(access_comp)

    areas: list[dict] = []
    urgent: dict[str, dict] = {}

    def add_urgent(sid: str, reason: str, priority: str, score: int, detail: str, area_id: str | None = None) -> None:
        current = urgent.get(sid)
        if current and current["score"] >= score:
            return
        segment = network.segments[sid]
        report = by_id.get(sid)
        urgent[sid] = {
            "segment_id": sid,
            "name": segment.name,
            "highway": segment.highway,
            "ref": segment.ref,
            "osm_bridge": segment.osm_bridge,
            "length_m": round(segment.length_m, 1),
            "lat": segment.mid_lat,
            "lng": segment.mid_lng,
            "condition": report.condition if report else "unknown",
            "data_class": data_class(report),
            "reason": reason,
            "priority": priority,
            "detail": detail,
            "area_id": area_id,
            "score": score,
        }

    for comp in components:
        comp_set = set(comp)
        if access in comp_set:
            continue
        internal = [sid for u, v, sid in all_edges if u in comp_set and v in comp_set]
        cut = [sid for u, v, sid in all_edges if real_blocked(sid) and ((u in comp_set) ^ (v in comp_set))]
        kinds = [_report_kind(by_id.get(sid) or inherited.get(sid)) for sid in cut]
        if kinds and all(kind == "verified" for kind in kinds):
            basis = "verified_blockage"
        elif kinds and all(kind == "unverified" for kind in kinds):
            basis = "unverified_report"
        elif kinds and all(kind == "simulated" for kind in kinds):
            basis = "simulated"
        else:
            basis = "mixed"
        area = _make_area(
            network,
            kind="blocked_off",
            basis=basis,
            node_ids=comp_set,
            internal_ids=internal,
            hinge_ids=[],
            cut_ids=cut,
            incidents=incidents,
            dominant=False,
        )
        area["summary"] = _blocked_summary(area, network, by_id)
        areas.append(area)
        for sid in cut:
            report = by_id.get(sid)
            if report is None or report.verification == "verified":
                continue
            add_urgent(
                sid,
                "unverified_blockage",
                "high",
                1000 + area["node_count"],
                "Unverified blockage report on the cut around this pocket. Confirm it or clear it. It is not an official closure.",
                area["id"],
            )

    hinges = _bridges_away_from(access, access_set, [edge for edge in opt_edges if edge[0] in access_set and edge[1] in access_set])
    hinges.sort(key=lambda item: len(item[1]), reverse=True)
    covered: set[int] = set()
    for sid, pocket in hinges:
        if len(pocket) < min_hinge_nodes:
            continue
        if pocket and len(pocket & covered) / len(pocket) >= 0.7:
            continue
        report = by_id.get(sid)
        if real_passable(sid, verified_only=True):
            continue
        basis = _link_basis(report)
        internal = [edge_id for u, v, edge_id in all_edges if u in pocket and v in pocket]
        area = _make_area(
            network,
            kind="uncertain_link",
            basis=basis,
            node_ids=pocket,
            internal_ids=internal,
            hinge_ids=[sid],
            cut_ids=[],
            incidents=incidents,
            dominant=False,
        )
        area["summary"] = _hinge_summary(area, network, report)
        areas.append(area)
        covered |= pocket
        label = network.segments[sid].name or "unnamed segment"
        add_urgent(
            sid,
            "last_link",
            "high",
            800 + area["node_count"],
            f"Only remaining connection for {area['node_count']} junctions ({label}). Condition is {area['link_state']}.",
            area["id"],
        )

    verified_edges = [edge for edge in all_edges if real_passable(edge[2], verified_only=True)]
    passable_edges = [edge for edge in all_edges if real_passable(edge[2])]
    verified_reach = _reachable(access, verified_edges)
    reported_reach = _reachable(access, passable_edges)
    unverified_nodes = reported_reach - verified_reach
    if unverified_nodes:
        corridor = [
            sid
            for u, v, sid in passable_edges
            if not real_passable(sid, verified_only=True) and u in reported_reach and v in reported_reach
        ]
        area = _make_area(
            network,
            kind="unverified_access",
            basis="unverified_report",
            node_ids=unverified_nodes,
            internal_ids=corridor,
            hinge_ids=corridor,
            cut_ids=[],
            incidents=incidents,
            dominant=False,
        )
        area["summary"] = (
            f"{area['node_count']} junctions can be reached from the western entry only across "
            "roads reported passable and not verified. That corridor is unconfirmed."
        )
        areas.append(area)
        passable_bridges = {bridge_id for bridge_id, _pocket in _bridges_away_from(access, reported_reach, passable_edges)}
        for sid in corridor:
            if sid not in passable_bridges and len(corridor) > 6:
                continue
            add_urgent(
                sid,
                "unverified_passable",
                "high",
                600,
                "Part of the reachable network depends on this unverified passable report.",
                area["id"],
            )

    unreached = access_set - reported_reach
    hinge_cover = covered
    remaining = unreached - hinge_cover
    if unreached and len(remaining) / max(1, len(access_set)) >= 0.45:
        area = _make_area(
            network,
            kind="uncertain_access",
            basis="unknown_segments",
            node_ids=remaining,
            internal_ids=[],
            hinge_ids=[],
            cut_ids=[],
            incidents=[],
            dominant=True,
        )
        area["segment_count"] = sum(1 for u, v, _sid in opt_edges if u in remaining and v in remaining)
        area["summary"] = (
            "Most mapped junctions still have no reported-passable route from the western entry. "
            "Those roads are unknown: unreported, not marked safe, and not a hurricane closure."
        )
        areas.append(area)

    frontier = []
    for u, v, sid in opt_edges:
        if real_passable(sid):
            continue
        if real_blocked(sid):
            continue
        if (u in reported_reach) ^ (v in reported_reach):
            frontier.append(sid)
    frontier.sort(key=lambda sid: _frontier_key(network.segments[sid]), reverse=True)
    for sid in frontier[:8]:
        if sid in urgent:
            continue
        add_urgent(
            sid,
            "entry_frontier",
            "medium",
            200 + int(HIGHWAY_RANK.get(network.segments[sid].highway or "", 0)),
            "No reported-passable route crosses this segment from the current known entry. Checking it is the next verification step.",
            None,
        )

    for sid, report in by_id.items():
        if report.condition not in {"blocked", "damaged"} or report.verification == "verified":
            continue
        if report.source == "simulation" and not apply_simulated:
            continue
        if sid not in urgent:
            add_urgent(
                sid,
                "unverified_blockage",
                "high",
                900,
                "Unverified blockage report. It changes the working map and still needs confirmation. It is not an official closure.",
                None,
            )

    ordered = sorted(urgent.values(), key=lambda item: ({"high": 0, "medium": 1}[item["priority"]], -item["score"], item["segment_id"]))
    for item in ordered:
        item.pop("score", None)

    counts = _counts(network, by_id)
    access_lat, access_lng = network.nodes[access]
    limitations = [
        "Road lines are an OpenStreetMap extract for Swannanoa. They are not live closure data.",
        "Unknown means no demo report is saved. It does not mean the road is passable.",
        (
            "Simulated drill blockages are included in this analysis and every result from them is still labeled simulated. They are not Hurricane Helene closures."
            if apply_simulated
            else "Simulated drill markings are shown and stored, and they do not change which areas are isolated unless the drill toggle is on."
        ),
        "Verified means an operator marked that report verified inside this demo. It is not a DOT or emergency-management status.",
        "Isolation is measured from one western junction in the extract, toward Asheville. Other approaches are not scored.",
        "A blockage is also applied to the opposite OpenStreetMap edge with the same key when that edge has no report of its own. Other one-way restrictions are ignored. The toy scenario route is a separate simulated graph.",
    ]
    return {
        "disclaimer": DISCLAIMER,
        "simulation_applied": apply_simulated,
        "policy": (
            "This drill is applying simulated blockages. They are removed from the working map and labeled simulated. They are not historical or current closures. Unknown roads stay as possible connections."
            if apply_simulated
            else "Isolation ignores simulated markings. Real blockage reports are removed from the working map. Unknown roads stay as possible connections until a passable report exists."
        ),
        "access": _access_payload(network, access_lat, access_lng),
        "network": {
            "segments": len(network.segments),
            "junctions": len(network.nodes),
            "components_before_reports": network.component_count,
            "osm_bridges": network.osm_bridge_count,
        },
        "counts": counts,
        "areas": areas,
        "urgent": ordered,
        "simulated_reports": [serialize_report(network, report) for report in reports if report.source == "simulation"],
        "limitations": limitations,
    }


def _access_payload(network: Network, lat: float, lng: float) -> dict:
    return {
        "node_id": network.access_node,
        "lat": lat,
        "lng": lng,
        "description": "Western high-connectivity junction in the Swannanoa OpenStreetMap extract, toward Asheville. Not a shelter or staging area.",
    }


def _report_kind(report: Report | None) -> str:
    if report is None or report.condition == "unknown":
        return "unknown"
    if report.source == "simulation":
        return "simulated"
    if report.verification == "verified":
        return "verified"
    return "unverified"


def _link_basis(report: Report | None) -> str:
    if report and report.source == "simulation":
        return "simulated"
    if report and report.condition == "passable" and report.verification != "verified":
        return "unverified_report"
    return "unknown_segments"


def _counts(network: Network, by_id: dict[str, Report]) -> dict:
    counts = {
        "segments": len(network.segments),
        "unknown": 0,
        "reported_passable_unverified": 0,
        "reported_blocked_unverified": 0,
        "reported_damaged_unverified": 0,
        "verified_passable": 0,
        "verified_blocked": 0,
        "verified_damaged": 0,
        "simulated": 0,
    }
    reported = set(by_id)
    counts["unknown"] = counts["segments"] - len(reported)
    for report in by_id.values():
        if report.source == "simulation":
            counts["simulated"] += 1
        elif report.verification == "verified" and report.condition == "passable":
            counts["verified_passable"] += 1
        elif report.verification == "verified" and report.condition == "blocked":
            counts["verified_blocked"] += 1
        elif report.verification == "verified" and report.condition == "damaged":
            counts["verified_damaged"] += 1
        elif report.condition == "passable":
            counts["reported_passable_unverified"] += 1
        elif report.condition == "blocked":
            counts["reported_blocked_unverified"] += 1
        elif report.condition == "damaged":
            counts["reported_damaged_unverified"] += 1
        else:
            counts["unknown"] += 1
    return counts


def _place_name(network: Network, segment_ids: list[str], node_ids: set[int]) -> str:
    names = [network.segments[sid].name for sid in segment_ids if sid in network.segments and network.segments[sid].name]
    if names:
        return max(set(names), key=names.count)
    if node_ids:
        lat = sum(network.nodes[node_id][0] for node_id in node_ids) / len(node_ids)
        lng = sum(network.nodes[node_id][1] for node_id in node_ids) / len(node_ids)
        return f"near {lat:.3f}, {lng:.3f}"
    return "mapped pocket"


def _make_area(
    network: Network,
    kind: str,
    basis: str,
    node_ids: set[int],
    internal_ids: list[str],
    hinge_ids: list[str],
    cut_ids: list[str],
    incidents: list[dict],
    dominant: bool,
) -> dict:
    label_ids = hinge_ids or cut_ids or internal_ids
    title_name = _place_name(network, label_ids, node_ids)
    titles = {
        "blocked_off": f"Cut off around {title_name}",
        "uncertain_link": f"Single link at {title_name}",
        "uncertain_access": "Unreported network",
        "unverified_access": "Unverified passable corridor",
    }
    listed = [] if dominant or len(internal_ids) > 400 else internal_ids
    lat = sum(network.nodes[node_id][0] for node_id in node_ids) / len(node_ids)
    lng = sum(network.nodes[node_id][1] for node_id in node_ids) / len(node_ids)
    link_state = "unknown"
    if hinge_ids:
        link_state = data_class(None)
        # Caller may overwrite after seeing the report; default is unknown.
    return {
        "id": _area_id(kind, node_ids, hinge_ids or cut_ids),
        "kind": kind,
        "evidence_basis": basis,
        "title": titles[kind],
        "summary": "",
        "node_count": len(node_ids),
        "segment_count": len(internal_ids),
        "segment_ids": listed,
        "hinge_segment_ids": hinge_ids,
        "cut_segment_ids": cut_ids,
        "dominant": dominant,
        "centroid": {"lat": round(lat, 6), "lng": round(lng, 6)},
        "nearby_incidents": [] if dominant else _nearby(network, node_ids, incidents),
        "link_state": link_state,
    }


def _area_id(kind: str, node_ids: set[int], key_ids: list[str]) -> str:
    if key_ids:
        token = key_ids[0].strip("()").replace(", ", "-")
        return f"{kind}-{token}"
    return f"{kind}-{min(node_ids)}"


def _blocked_summary(area: dict, network: Network, by_id: dict[str, Report]) -> str:
    names = [network.segments[sid].name or sid for sid in area["cut_segment_ids"][:3]]
    roads = ", ".join(names) if names else "reported blocked segments"
    junctions = f"{area['node_count']} junction" if area["node_count"] == 1 else f"{area['node_count']} junctions"
    if area["evidence_basis"] == "verified_blockage":
        return (
            f"{junctions} cannot reach the western entry even if every unknown road is open. "
            f"The cut is a demo-verified blockage ({roads}). Verified here is an operator flag, not an official closure."
        )
    if area["evidence_basis"] == "unverified_report":
        return (
            f"{junctions} cannot reach the western entry even if every unknown road is open. "
            f"The cut is an unverified report ({roads}), so this is potential isolation, not a confirmed closure."
        )
    if area["evidence_basis"] == "simulated":
        return (
            f"{junctions} cannot reach the western entry even if every unknown road is open. "
            f"The cut is a simulated drill blockage ({roads}). It is not a Hurricane Helene or NCDOT closure."
        )
    return (
        f"{junctions} cannot reach the western entry even if every unknown road is open. "
        f"The cut mixes verified and unverified demo reports ({roads})."
    )


def _hinge_summary(area: dict, network: Network, report: Report | None) -> str:
    sid = area["hinge_segment_ids"][0]
    segment = network.segments[sid]
    name = segment.name or "an unnamed segment"
    state = "unknown (no report)"
    area["link_state"] = "unknown"
    if report and report.source == "simulation":
        state = "a simulated drill marking, which is not used as a real condition"
        area["link_state"] = "simulated"
    elif report and report.condition == "passable":
        state = "an unverified passable report"
        area["link_state"] = "unverified_report"
    return (
        f"{area['node_count']} junctions stay connected through one road, {name}. "
        f"That link is {state}. If it is impassable, this pocket is isolated. "
        "This comes from the OSM network plus demo reports, not from a hurricane closure list."
    )


def _nearby(network: Network, node_ids: set[int], incidents: list[dict]) -> list[dict]:
    hits = []
    for incident in incidents:
        best = None
        for node_id in node_ids:
            lat, lng = network.nodes[node_id]
            distance = haversine_m(incident["lat"], incident["lng"], lat, lng)
            if best is None or distance < best:
                best = distance
        if best is not None and best <= 800:
            hits.append(
                {
                    "id": incident["id"],
                    "place": incident.get("place"),
                    "people": incident.get("people"),
                    "source": incident.get("source"),
                    "distance_m": round(best),
                    "data_class": "simulated" if str(incident.get("source", "")).startswith("seed") or incident.get("source") in {"scenario", "seeded_simulation"} else "demo_record",
                }
            )
    hits.sort(key=lambda item: item["distance_m"])
    return hits[:5]


def _frontier_key(segment: Segment) -> tuple:
    return (
        1 if segment.osm_bridge else 0,
        HIGHWAY_RANK.get(segment.highway or "", 0),
        segment.length_m,
    )


def _components(nodes: set[int], edges: list[tuple[int, int, str]]) -> list[list[int]]:
    adj: dict[int, set[int]] = defaultdict(set)
    for u, v, _sid in edges:
        if u == v:
            continue
        adj[u].add(v)
        adj[v].add(u)
    seen: set[int] = set()
    components: list[list[int]] = []
    for node in nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        comp: list[int] = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for nxt in adj[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(comp)
    return components


def _reachable(start: int, edges: list[tuple[int, int, str]]) -> set[int]:
    adj: dict[int, set[int]] = defaultdict(set)
    for u, v, _sid in edges:
        if u == v:
            continue
        adj[u].add(v)
        adj[v].add(u)
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for nxt in adj[current]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _bridges_away_from(access: int, component: set[int], edges: list[tuple[int, int, str]]) -> list[tuple[str, set[int]]]:
    """Return (segment id, node set on the far side of the bridge) for one component."""
    adj: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for index, (u, v, _sid) in enumerate(edges):
        if u == v or u not in component or v not in component:
            continue
        adj[u].append((v, index))
        adj[v].append((u, index))
    tin: dict[int, int] = {}
    low: dict[int, int] = {}
    seen: set[int] = set()
    found: list[tuple[str, set[int]]] = []
    timer = 0

    def walk(node: int, parent_edge: int) -> set[int]:
        nonlocal timer
        seen.add(node)
        tin[node] = low[node] = timer
        timer += 1
        members = {node}
        for nxt, edge_index in adj[node]:
            if edge_index == parent_edge:
                continue
            if nxt in seen:
                low[node] = min(low[node], tin[nxt])
                continue
            child = walk(nxt, edge_index)
            members |= child
            low[node] = min(low[node], low[nxt])
            if low[nxt] > tin[node]:
                if access in child:
                    pocket = set(component) - child
                else:
                    pocket = set(child)
                pocket.discard(access)
                if pocket:
                    found.append((edges[edge_index][2], pocket))
        return members

    for node in component:
        if node not in seen:
            walk(node, -1)
    return found
