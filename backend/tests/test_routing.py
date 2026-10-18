from app.geo import is_geographic
from app.routing import build_graph, compute_route, load_anchors, load_graph
from pathlib import Path

from tests.support import anchors, graph

DATA = Path(__file__).resolve().parents[1] / "data"


def test_connected_graph_returns_a_path():
    route = compute_route(graph(), (-82.40, 35.60), (-82.38, 35.60), [])
    assert route["status"] == "ok"
    assert route["edge_ids"] == ["ab", "bc"]
    assert "bc" in route["edge_ids"]


def test_closed_edge_is_avoided_when_another_path_exists():
    route = compute_route(graph(), (-82.40, 35.60), (-82.38, 35.60), ["bc"])
    assert route["status"] == "ok"
    assert "bc" not in route["edge_ids"]
    assert route["edge_ids"] == ["ae", "ec"]


def test_blocked_graph_is_unreachable_and_has_no_invented_path():
    route = compute_route(graph(), (-82.40, 35.60), (-82.38, 35.60), ["ab", "bc", "ae", "ec"])
    assert route["status"] == "unreachable"
    assert route["geometry"] == []
    assert route["edge_ids"] == []


def test_pixel_polygons_are_not_treated_as_geography():
    assert is_geographic({"type": "Polygon", "coordinates": [[[-82.4, 35.6], [-82.39, 35.6], [-82.39, 35.61], [-82.4, 35.6]]]})
    assert not is_geographic({"type": "Polygon", "coordinates": [[[12, 40], [80, 40], [80, 400], [12, 40]]]})


def test_real_corridor_closure_changes_the_path():
    if not (DATA / "graph.json").exists():
        return
    road_graph = load_graph()
    points = load_anchors()
    origin = (points["origin"]["lon"], points["origin"]["lat"])
    destination = (points["destination"]["lon"], points["destination"]["lat"])
    first = compute_route(road_graph, origin, destination, [])
    assert first["status"] == "ok"
    closed = set(points["closure_edge_ids"])
    assert closed.intersection(first["edge_ids"])
    second = compute_route(road_graph, origin, destination, closed)
    if second["status"] == "ok":
        assert not closed.intersection(second["edge_ids"])
        assert second["edge_ids"] != first["edge_ids"]
    else:
        assert second["status"] == "unreachable"


def test_build_graph_accepts_edges_without_stored_geometry():
    bare = build_graph(
        [
            {
                "id": "only",
                "u": "-82.40000,35.60000",
                "v": "-82.39000,35.60000",
                "length": 100,
                "name": "Bare",
                "highway": "residential",
                "bridge": False,
                "way_id": 9,
            }
        ]
    )
    assert bare.number_of_edges() == 1
    assert anchors()["closure_name"] == "Test Bridge"
