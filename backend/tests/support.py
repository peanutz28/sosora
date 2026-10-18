from app.routing import build_graph


def nid(lon: float, lat: float) -> str:
    return f"{lon:.5f},{lat:.5f}"


A = (-82.40, 35.60)
B = (-82.39, 35.60)
C = (-82.38, 35.60)
E = (-82.39, 35.61)


def edge(edge_id, start, end, length, name="Test Road", highway="secondary", bridge=False):
    return {
        "id": edge_id,
        "u": nid(*start),
        "v": nid(*end),
        "length": length,
        "name": name,
        "highway": highway,
        "bridge": bridge,
        "way_id": 1,
        "geometry": [list(start), list(end)],
    }


def graph():
    return build_graph(
        [
            edge("ab", A, B, 900, "Main Street"),
            edge("bc", B, C, 900, "Test Bridge", bridge=True),
            edge("ae", A, E, 1100, "Ridge Road"),
            edge("ec", E, C, 1400, "Ridge Road"),
        ]
    )


def anchors():
    return {
        "origin": {"lon": A[0], "lat": A[1]},
        "destination": {"lon": C[0], "lat": C[1]},
        "closure_edge_ids": ["bc"],
        "closure_geometry": [list(B), list(C)],
        "closure_name": "Test Bridge",
        "closure_highway": "secondary",
        "region": "Test grid",
        "retrieved": "2026-10-17",
    }
