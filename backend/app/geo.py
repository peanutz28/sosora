from __future__ import annotations

import math


def buffer_line(coords: list, meters: float = 18.0):
    if len(coords) < 2:
        return None
    left = []
    right = []
    for index in range(len(coords) - 1):
        lon1, lat1 = coords[index]
        lon2, lat2 = coords[index + 1]
        mid_lat = (lat1 + lat2) / 2
        meters_lon = 111_320 * math.cos(math.radians(mid_lat))
        meters_lat = 111_320.0
        dx = (lon2 - lon1) * meters_lon
        dy = (lat2 - lat1) * meters_lat
        length = math.hypot(dx, dy) or 1.0
        ox = (-dy / length) * meters / meters_lon
        oy = (dx / length) * meters / meters_lat
        if index == 0:
            left.append([lon1 + ox, lat1 + oy])
            right.append([lon1 - ox, lat1 - oy])
        left.append([lon2 + ox, lat2 + oy])
        right.append([lon2 - ox, lat2 - oy])
    ring = left + list(reversed(right))
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def is_geographic(geometry: dict) -> bool:
    coords = []

    def walk(value):
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (int, float)):
            coords.append(value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates", []))
    if len(coords) < 3:
        return False
    return all(-180 <= point[0] <= 180 and -90 <= point[1] <= 90 for point in coords)
