from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import networkx as nx

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def build_graph(edges: Iterable[dict]) -> nx.MultiDiGraph:
    graph: nx.MultiDiGraph = nx.MultiDiGraph()
    for edge in edges:
        u = edge["u"]
        v = edge["v"]
        ulon, ulat = _xy(u)
        vlon, vlat = _xy(v)
        graph.add_node(u, lon=ulon, lat=ulat)
        graph.add_node(v, lon=vlon, lat=vlat)
        geometry = edge.get("geometry") or [[ulon, ulat], [vlon, vlat]]
        graph.add_edge(
            u,
            v,
            id=edge["id"],
            length=float(edge["length"]),
            name=edge.get("name") or "Unnamed segment",
            highway=edge.get("highway") or "road",
            bridge=bool(edge.get("bridge")),
            way_id=edge.get("way_id"),
            geometry=geometry,
        )
    return graph


def _xy(node_id: str) -> tuple:
    lon, lat = node_id.split(",")
    return float(lon), float(lat)


def nearest_node(graph: nx.MultiDiGraph, lon: float, lat: float):
    best = None
    best_distance = float("inf")
    for node, data in graph.nodes(data=True):
        distance = haversine_m(lon, lat, data["lon"], data["lat"])
        if distance < best_distance:
            best = node
            best_distance = distance
    if best is None:
        raise ValueError("graph has no nodes")
    return best, best_distance


def _usable(graph: nx.MultiDiGraph, closed: set) -> nx.MultiDiGraph:
    if not closed:
        return graph

    def allow(u, v, key):
        return graph.edges[u, v, key]["id"] not in closed

    return nx.subgraph_view(graph, filter_edge=allow)


def _assemble(graph: nx.MultiDiGraph, path: list, closed: set) -> dict:
    edge_ids = []
    coords = []
    length = 0.0
    names = []
    for start, end in zip(path[:-1], path[1:]):
        choices = [data for data in graph.get_edge_data(start, end).values() if data["id"] not in closed]
        edge = min(choices, key=lambda item: item["length"])
        edge_ids.append(edge["id"])
        length += float(edge["length"])
        if edge["name"] not in names:
            names.append(edge["name"])
        geometry = edge["geometry"]
        if not coords:
            coords.extend(geometry)
        else:
            coords.extend(geometry[1:])
    return {
        "status": "ok",
        "length_m": round(length, 1),
        "edge_ids": edge_ids,
        "edge_count": len(edge_ids),
        "geometry": coords,
        "roads": names[:8],
    }


def compute_route(graph: nx.MultiDiGraph, origin: tuple, destination: tuple, closed: Iterable[str] = ()) -> dict:
    banned = set(closed or [])
    origin_node, origin_snap = nearest_node(graph, origin[0], origin[1])
    destination_node, destination_snap = nearest_node(graph, destination[0], destination[1])
    meta = {
        "origin_snap_m": round(origin_snap, 1),
        "destination_snap_m": round(destination_snap, 1),
    }
    empty = {
        **meta,
        "length_m": None,
        "edge_ids": [],
        "edge_count": 0,
        "geometry": [],
        "roads": [],
    }
    if origin_snap > 800 or destination_snap > 800:
        return {**empty, "status": "snap_failed"}
    if origin_node == destination_node:
        lon, lat = _xy(origin_node)
        return {**meta, "status": "ok", "length_m": 0.0, "edge_ids": [], "edge_count": 0, "geometry": [[lon, lat]], "roads": []}
    try:
        path = nx.shortest_path(_usable(graph, banned), origin_node, destination_node, weight="length")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {**empty, "status": "unreachable"}
    route = _assemble(graph, path, banned)
    route.update(meta)
    if banned.intersection(route["edge_ids"]):
        raise RuntimeError("computed route includes a closed edge")
    return route


def load_graph(path: Path = None) -> nx.MultiDiGraph:
    graph_path = path or (DATA_DIR / "graph.json")
    payload = json.loads(graph_path.read_text())
    return build_graph(payload["edges"])


def incident_routes(graph, bases, incidents, closed=(), snap_cache=None) -> dict:
    """One Dijkstra per selected base, preserving compute_route's wire format.

    Road nodes are immutable for an engine's lifetime, so callers may retain snaps
    across reports. Paths are always recomputed against the current closure set.
    Multiple rescue bases retain the existing nearest-base-by-distance policy.
    """
    if not incidents:
        return {}
    snaps = snap_cache if snap_cache is not None else {}

    def snap(point):
        if point not in snaps:
            snaps[point] = nearest_node(graph, *point)
        return snaps[point]

    groups = {}
    for incident in incidents:
        base = min(bases, key=lambda b: haversine_m(b["lon"], b["lat"], incident["lon"], incident["lat"]))
        groups.setdefault((base["lon"], base["lat"]), []).append(incident)
    banned = set(closed or [])
    usable = _usable(graph, banned)
    result = {}
    for origin, targets in groups.items():
        origin_node, origin_snap = snap(origin)
        paths = nx.single_source_dijkstra(usable, origin_node, weight="length")[1] if origin_snap <= 800 else {}
        for incident in targets:
            destination_node, destination_snap = snap((incident["lon"], incident["lat"]))
            meta = {"origin_snap_m": round(origin_snap, 1), "destination_snap_m": round(destination_snap, 1)}
            empty = {**meta, "length_m": None, "edge_ids": [], "edge_count": 0, "geometry": [], "roads": []}
            if origin_snap > 800 or destination_snap > 800:
                route = {**empty, "status": "snap_failed"}
            elif origin_node == destination_node:
                route = {**meta, "status": "ok", "length_m": 0.0, "edge_ids": [], "edge_count": 0,
                         "geometry": [list(_xy(origin_node))], "roads": []}
            elif destination_node not in paths:
                route = {**empty, "status": "unreachable"}
            else:
                route = {**_assemble(graph, paths[destination_node], banned), **meta}
            result[incident["id"]] = route
    return result


def load_anchors(path: Path = None) -> dict:
    anchor_path = path or (DATA_DIR / "anchors.json")
    return json.loads(anchor_path.read_text())
