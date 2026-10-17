"""Build a cached OpenStreetMap drive graph for the Swannanoa corridor.

Reads backend/data/osm_raw.json, writes graph.json, roads.geojson, and anchors.json.
The anchor selector searches real paths, closes a real edge, and keeps the closure
only when the graph result changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.routing import build_graph, compute_route, haversine_m

RAW = ROOT / "data" / "osm_raw.json"
ALLOWED = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
}
PAIRS = [
    ((-82.430, 35.590), (-82.360, 35.600)),
    ((-82.450, 35.585), (-82.380, 35.605)),
    ((-82.420, 35.575), (-82.350, 35.610)),
    ((-82.470, 35.590), (-82.340, 35.600)),
    ((-82.492, 35.596), (-82.318, 35.618)),
]


def node_id(lon: float, lat: float) -> str:
    return f"{lon:.5f},{lat:.5f}"


def directions(tags: dict) -> tuple:
    oneway = tags.get("oneway", "no")
    if oneway in {"yes", "true", "1"} or tags.get("junction") == "roundabout":
        return True, False
    if oneway in {"-1", "reverse"}:
        return False, True
    return True, True


def rank(highway: str) -> int:
    if highway in {"motorway", "motorway_link", "trunk", "trunk_link"}:
        return 1
    if highway in {"primary", "primary_link", "secondary", "secondary_link"}:
        return 2
    return 3


def expand(path_edges: list, center: int, minimum: float = 140.0) -> list:
    chosen = [path_edges[center]]
    total = chosen[0]["length"]
    left = center - 1
    right = center + 1
    while total < minimum and (left >= 0 or right < len(path_edges)):
        if right < len(path_edges):
            chosen.append(path_edges[right])
            total += path_edges[right]["length"]
            right += 1
        if total >= minimum:
            break
        if left >= 0:
            chosen.insert(0, path_edges[left])
            total += path_edges[left]["length"]
            left -= 1
    return chosen


def merged_geometry(edges: list) -> list:
    coords = []
    for edge in edges:
        if not coords:
            coords.extend(edge["geometry"])
        else:
            coords.extend(edge["geometry"][1:])
    return coords


def divergence(first: list, second: list) -> float:
    sample_a = first[:: max(1, len(first) // 40)]
    sample_b = second[:: max(1, len(second) // 40)]
    distances = []
    for point in sample_b:
        distances.append(min(haversine_m(point[0], point[1], other[0], other[1]) for other in sample_a))
    distances.sort()
    return distances[len(distances) // 2]


def edge_lookup(graph) -> dict:
    found = {}
    for u, v, data in graph.edges(data=True):
        found[data["id"]] = data
    return found


def choose(graph, lookup: dict) -> dict:
    best = None
    for origin, destination in PAIRS:
        first = compute_route(graph, origin, destination, [])
        if first["status"] != "ok" or not (1_500 <= first["length_m"] <= 30_000):
            print(
                "skip pair",
                origin,
                destination,
                first["status"],
                first.get("length_m"),
                "snap",
                first.get("origin_snap_m"),
                first.get("destination_snap_m"),
            )
            continue
        path_edges = [lookup[edge_id] for edge_id in first["edge_ids"]]
        bridge_indexes = [index for index, edge in enumerate(path_edges) if edge["bridge"]]
        middle = list(range(int(len(path_edges) * 0.25), max(int(len(path_edges) * 0.25) + 1, int(len(path_edges) * 0.75))))
        candidates = bridge_indexes or middle
        if len(candidates) > 16:
            step = max(1, len(candidates) // 16)
            candidates = candidates[::step][:16]
        for index in candidates:
            group = expand(path_edges, index)
            closed = [edge["id"] for edge in group]
            second = compute_route(graph, origin, destination, closed)
            if second["status"] == "ok":
                if set(closed).intersection(second["edge_ids"]):
                    continue
                spread = divergence(first["geometry"], second["geometry"])
                score = (0, -spread, abs(first["length_m"] - 6_000) / 1_000)
            else:
                score = (1, 0, abs(first["length_m"] - 6_000) / 1_000)
                spread = None
            record = {
                "score": score,
                "origin": origin,
                "destination": destination,
                "first": first,
                "second": second,
                "group": group,
                "spread": spread,
            }
            if best is None or score < best["score"]:
                best = record
    if best is None:
        raise SystemExit("no usable origin/destination pair on this graph")
    return best


def main() -> None:
    raw = json.loads(RAW.read_text())
    edges = []
    features = []
    for element in raw["elements"]:
        if element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        highway = tags.get("highway")
        if highway not in ALLOWED:
            continue
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        name = tags.get("name") or tags.get("ref") or "Unnamed segment"
        bridge = tags.get("bridge") in {"yes", "viaduct", "aqueduct", "boardwalk"}
        forward, backward = directions(tags)
        way_id = element["id"]
        features.append(
            {
                "type": "Feature",
                "properties": {"way_id": way_id, "name": name, "highway": highway, "rank": rank(highway), "bridge": bridge},
                "geometry": {"type": "LineString", "coordinates": [[point["lon"], point["lat"]] for point in geometry]},
            }
        )
        for index in range(len(geometry) - 1):
            start = geometry[index]
            end = geometry[index + 1]
            start_id = node_id(start["lon"], start["lat"])
            end_id = node_id(end["lon"], end["lat"])
            if start_id == end_id:
                continue
            length = haversine_m(start["lon"], start["lat"], end["lon"], end["lat"])
            if length < 0.4:
                continue
            segment = [[start["lon"], start["lat"]], [end["lon"], end["lat"]]]
            base = {
                "length": round(length, 2),
                "name": name,
                "highway": highway,
                "bridge": bridge,
                "way_id": way_id,
                "geometry": segment,
            }
            if forward:
                edges.append({**base, "id": f"{way_id}:{index}:f", "u": start_id, "v": end_id})
            if backward:
                edges.append({**base, "id": f"{way_id}:{index}:b", "u": end_id, "v": start_id, "geometry": list(reversed(segment))})

    graph = build_graph(edges)
    print(f"nodes {graph.number_of_nodes()} edges {graph.number_of_edges()} ways {len(features)}")
    chosen = choose(graph, edge_lookup(graph))
    group = chosen["group"]
    origin = {"lon": chosen["origin"][0], "lat": chosen["origin"][1]}
    destination = {"lon": chosen["destination"][0], "lat": chosen["destination"][1]}
    # Persist the snapped coordinates so runtime snap distance is ~0.
    origin_snap = chosen["first"]["geometry"][0]
    destination_snap = chosen["first"]["geometry"][-1]
    names = [edge["name"] for edge in group if edge["name"] != "Unnamed segment"]
    closure_name = names[0] if names else group[0]["name"]
    outcome = "reroute" if chosen["second"]["status"] == "ok" else "unreachable"
    anchors = {
        "origin": {"lon": origin_snap[0], "lat": origin_snap[1], "target": origin},
        "destination": {"lon": destination_snap[0], "lat": destination_snap[1], "target": destination},
        "closure_edge_ids": [edge["id"] for edge in group],
        "closure_geometry": merged_geometry(group),
        "closure_name": closure_name,
        "closure_highway": group[len(group) // 2]["highway"],
        "closure_is_bridge": any(edge["bridge"] for edge in group),
        "expected_outcome": outcome,
        "initial_length_m": chosen["first"]["length_m"],
        "replacement_length_m": chosen["second"].get("length_m"),
        "divergence_m": None if chosen["spread"] is None else round(chosen["spread"], 1),
        "region": "Swannanoa corridor, Buncombe County, North Carolina",
        "retrieved": "2026-10-17",
        "source": "OpenStreetMap via Overpass (overpass.openstreetmap.fr)",
    }
    stored_edges = []
    for edge in edges:
        stored = dict(edge)
        stored.pop("geometry", None)
        stored_edges.append(stored)
    (ROOT / "data" / "graph.json").write_text(
        json.dumps(
            {
                "retrieved": "2026-10-17",
                "source": anchors["source"],
                "note": "Current OpenStreetMap drive network. Not a 27 September 2024 snapshot.",
                "edges": stored_edges,
            },
            separators=(",", ":"),
        )
    )
    (ROOT / "data" / "roads.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    )
    (ROOT / "data" / "anchors.json").write_text(json.dumps(anchors, indent=2))
    print("closure", closure_name, "bridge", anchors["closure_is_bridge"], "outcome", outcome)
    print("length", anchors["initial_length_m"], "->", anchors["replacement_length_m"], "divergence", anchors["divergence_m"])
    print("origin", anchors["origin"])
    print("destination", anchors["destination"])


if __name__ == "__main__":
    main()
