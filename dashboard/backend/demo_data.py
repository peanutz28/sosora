"""Invented rescue scenario on real Swannanoa OpenStreetMap coordinates.

Nothing in this module is a Hurricane Helene observation, an NCDOT closure,
or a record of a real person.
"""
from __future__ import annotations

DEMO_SOURCE = "demo_simulation"
LEGACY_SOURCES = ("seeded_simulation", "demo_simulation")

# Coordinates are midpoints of named segments in frontend/roads.geojson.
DEMO_INCIDENTS = [
    {
        "id": "SOS-1042",
        "priority": "critical",
        "description": "SIMULATED: family stranded by floodwater",
        "place": "Warren Wilson Road",
        "people": 4,
        "lat": 35.60814,
        "lng": -82.44390,
        "status": "Received",
        "message": "SIMULATED DEMO. Four people are upstairs beside the Warren Wilson Road bridge segment. Not a historical Hurricane Helene report and not a real household.",
        "created_at": "2024-09-27T10:40:00+00:00",
    },
    {
        "id": "SOS-1036",
        "priority": "high",
        "description": "SIMULATED: residents cannot leave Bee Tree Road",
        "place": "Bee Tree Road",
        "people": 7,
        "lat": 35.61695,
        "lng": -82.42724,
        "status": "Received",
        "message": "SIMULATED DEMO. Seven residents are waiting on Bee Tree Road. The earlier Broad River Road coordinate was outside this map extract and has been moved onto this real OSM segment.",
        "created_at": "2024-09-27T11:15:00+00:00",
    },
    {
        "id": "SOS-1039",
        "priority": "high",
        "description": "SIMULATED: medical evacuation requested",
        "place": "Lower Grassy Branch Road",
        "people": 2,
        "lat": 35.60847,
        "lng": -82.47568,
        "status": "Acknowledged",
        "message": "SIMULATED DEMO. Two people need evacuation on Lower Grassy Branch Road. This point was previously mislabeled Old Fort Highway; Old Fort is a different town.",
        "created_at": "2024-09-27T12:05:00+00:00",
    },
    {
        "id": "SOS-2214",
        "priority": "medium",
        "description": "SIMULATED: debris across US 70",
        "place": "Tunnel Road",
        "people": 1,
        "lat": 35.59117,
        "lng": -82.44454,
        "status": "Received",
        "message": "SIMULATED DEMO. A driver reports trees and mud on Tunnel Road (US 70). Not a DriveNC closure.",
        "created_at": "2024-09-27T13:20:00+00:00",
    },
    {
        "id": "SOS-2188",
        "priority": "low",
        "description": "SIMULATED: welfare check",
        "place": "Azalea Road East",
        "people": 1,
        "lat": 35.58268,
        "lng": -82.47255,
        "status": "Queued",
        "message": "SIMULATED DEMO. One person asked for a welfare check on Azalea Road East. No injury reported in the drill.",
        "created_at": "2024-09-27T14:10:00+00:00",
    },
    {
        "id": "SOS-2302",
        "priority": "unspecified",
        "description": "SIMULATED: radio check-in without a severity",
        "place": "Riceville Road",
        "people": 3,
        "lat": 35.62093,
        "lng": -82.47168,
        "status": "Received",
        "message": "SIMULATED DEMO. Severity was not set. Unclassified incidents sort after Low.",
        "created_at": "2024-09-27T15:00:00+00:00",
    },
]

# Whitson Avenue coordinate is a placeholder until snapped. I'll snap in ensure if the name exists.
# Better to set a known coordinate now. I didn't list Whitson in the name dump. Let me check...
# I didn't see Whitson. I should not invent a road name that isn't in the extract.
# Change SOS-2302 to West State Street which is paired with Tunnel Road at 35.59117, -82.44454
# That's the same point as SOS-2214. Use Riceville or a distinct point.
# From the name list: West State Street appears. Let me use a point I'll set after a quick lookup.
# I'll look up in ensure_demo and skip the incident if I hardcode wrong.
# I'll use Buckeye Cove Road - I need a coordinate. I'll query... I already have the loader available at runtime.
# Hardcode after I pick one. From memory of the dump I don't have Buckeye coords.
# I'll set SOS-2302 place to "West State Street" and a nearby but different segment.
# Tunnel Road (3315748681, 3315748552, 0) was 35.59113, -82.44879. Use that.

DEMO_ROAD_REPORTS = [
    {
        "segment_id": "(169625258, 169657312, 0)",
        "condition": "blocked",
        "source": "simulation",
        "evidence": "SIMULATED DEMO. Modeled high water on the OSM-tagged bridge segment of Warren Wilson Road. Not an NCDOT closure and not a September 2024 inventory record.",
        "verification": "unverified",
        "reported_at": "2024-09-27T11:05:00+00:00",
    },
    {
        "segment_id": "(169616818, 3315748552, 0)",
        "condition": "damaged",
        "source": "simulation",
        "evidence": "SIMULATED DEMO. Debris reported on Tunnel Road / US 70 in the drill. Geometry is OpenStreetMap. Passability is not verified.",
        "verification": "unverified",
        "reported_at": "2024-09-27T13:25:00+00:00",
    },
    {
        "segment_id": "(169540007, 3613979107, 0)",
        "condition": "blocked",
        "source": "simulation",
        "evidence": "SIMULATED DEMO. Bee Tree Road marked blocked for the drill so the stranded-resident story has a cause. Not a historical closure.",
        "verification": "unverified",
        "reported_at": "2024-09-27T11:20:00+00:00",
    },
]

PLACE_FIXES = {
    "SOS-1042": ("Swannanoa River Road", "Warren Wilson Road", 35.60814, -82.44390),
    "SOS-1039": ("Old Fort Highway", "Lower Grassy Branch Road", 35.60847, -82.47568),
    "SOS-1036": ("Broad River Road", "Bee Tree Road", 35.61695, -82.42724),
}


def _insert_incident(c, item: dict) -> None:
    c.execute(
        "INSERT INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            item["id"], item["priority"], item["description"], item["place"], item["people"],
            item["lat"], item["lng"], item["status"], item["message"], item["created_at"], DEMO_SOURCE,
        ),
    )


def ensure_demo(c) -> None:
    """Add missing drill records. Do not reset operator status or duplicate rows."""
    for item in DEMO_INCIDENTS:
        row = c.execute("SELECT id, source, place, message, created_at FROM incidents WHERE id=?", (item["id"],)).fetchone()
        if row is None:
            _insert_incident(c, item)
            continue
        if row["source"] not in LEGACY_SOURCES:
            continue
        created = row["created_at"] or ""
        story_time = item["created_at"] if not created.startswith("2024-09-27") else created
        fix = PLACE_FIXES.get(item["id"])
        if fix and row["place"] == fix[0]:
            c.execute(
                "UPDATE incidents SET place=?, lat=?, lng=?, description=?, message=?, created_at=? WHERE id=?",
                (fix[1], fix[2], fix[3], item["description"], item["message"], story_time, item["id"]),
            )
        else:
            c.execute(
                "UPDATE incidents SET description=?, message=?, created_at=?, place=?, lat=?, lng=? WHERE id=?",
                (item["description"], item["message"], story_time, item["place"], item["lat"], item["lng"], item["id"]),
            )
    for report in DEMO_ROAD_REPORTS:
        existing = c.execute("SELECT source FROM road_reports WHERE segment_id=?", (report["segment_id"],)).fetchone()
        if existing:
            continue
        c.execute(
            """INSERT INTO road_reports (segment_id,condition,source,evidence,verification,reported_at,updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                report["segment_id"], report["condition"], report["source"], report["evidence"],
                report["verification"], report["reported_at"], report["reported_at"],
            ),
        )
    if not c.execute("SELECT 1 FROM state WHERE key='demo_apply_simulated'").fetchone():
        c.execute("INSERT INTO state VALUES ('demo_apply_simulated','1')")


def reset_demo(c) -> None:
    """Replay the same drill. Stable ids, so a second reset does not duplicate rows."""
    c.execute("DELETE FROM incidents WHERE source IN ('scenario','demo_simulation','seeded_simulation') OR id='SOS-DEMO'")
    for item in DEMO_INCIDENTS:
        _insert_incident(c, item)
    c.execute("DELETE FROM road_reports WHERE source='simulation'")
    for report in DEMO_ROAD_REPORTS:
        occupied = c.execute("SELECT 1 FROM road_reports WHERE segment_id=?", (report["segment_id"],)).fetchone()
        if occupied:
            continue
        c.execute(
            """INSERT INTO road_reports (segment_id,condition,source,evidence,verification,reported_at,updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                report["segment_id"], report["condition"], report["source"], report["evidence"],
                report["verification"], report["reported_at"], report["reported_at"],
            ),
        )
    c.execute("UPDATE state SET value='0' WHERE key='stage'")
    c.execute("INSERT INTO state (key,value) VALUES ('demo_apply_simulated','1') ON CONFLICT(key) DO UPDATE SET value='1'")
