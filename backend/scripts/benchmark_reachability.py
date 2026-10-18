"""Seed equality + timings against the unchanged per-incident compute_route oracle.

Run from backend/: DEMO_MODE=true python scripts/benchmark_reachability.py --output PATH
No model/network calls; full real OSM graph, three paired hero assessments.
"""
import argparse
import asyncio
import json
import os
import statistics
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DEMO_MODE'] = 'true'
from app.agent import RadioAgent
from app.factory import Hub
from app.radio_api import SEED, HERO, BEACON_POSITION, RadioIn, build_report, _fixture
from app.routing import compute_route, haversine_m, incident_routes, load_graph, load_anchors
from app.scenario import ScenarioEngine
from app.store import Store
from datetime import datetime, timezone


def old_routes(engine):
    bases = engine.anchors.get('rescue_bases') or [engine.anchors['origin']]
    result = {}
    for incident in engine.incidents:
        base = min(bases, key=lambda b: haversine_m(b['lon'], b['lat'], incident['lon'], incident['lat']))
        result[incident['id']] = compute_route(engine.graph, (base['lon'], base['lat']),
            (incident['lon'], incident['lat']), engine.closed_ids)
    return result


def seeded(network, anchors):
    engine = ScenarioEngine(network, anchors, Store(':memory:'))
    for cid, lon, lat, message, people, medical in SEED:
        engine.add_incident(dict(client_id=cid, lon=lon, lat=lat, message=message,
                                 people_affected=people, medical=medical))
    return engine


def main(output):
    network, anchors = load_graph(), load_anchors()
    bases = anchors.get('rescue_bases') or [anchors['origin']]
    report = build_report(_fixture(HERO), RadioIn(message=HERO, source_type='beacon', **BEACON_POSITION),
                          datetime.now(timezone.utc))
    samples = []
    comparisons = []
    for repeat in range(3):
        pair = {}
        outcomes = {}
        for mode in ('old', 'new') if repeat % 2 == 0 else ('new', 'old'):
            engine = seeded(network, anchors)
            route_fn = old_routes if mode == 'old' else lambda e: incident_routes(
                e.graph, bases, e.incidents, e.closed_ids, e.route_snaps)
            with patch.object(RadioAgent, 'routes', lambda agent: route_fn(agent.engine)):
                start = perf_counter()
                initial = route_fn(engine)
                seed_seconds = perf_counter() - start
                start = perf_counter()
                agent = RadioAgent(engine, Hub(), report)
                assessment = asyncio.run(agent.run())
                report_seconds = perf_counter() - start
                outcomes[mode] = {'initial': initial, 'after': {i['id']: i['route'] for i in engine.incidents},
                                  'assessment': assessment, 'statuses': agent.statuses}
            pair[mode] = dict(seed_routes_seconds=seed_seconds, hero_report_seconds=report_seconds)
        assert outcomes['old'] == outcomes['new'], 'Old/new full route or assessment outputs differ'
        comparisons.append(outcomes['new'])
        samples.append(pair)
    summary = {metric: {mode: statistics.median(s[mode][metric] for s in samples) for mode in ('old', 'new')}
               for metric in ('seed_routes_seconds', 'hero_report_seconds')}
    result = dict(graph_nodes=network.number_of_nodes(), graph_edges=network.number_of_edges(),
                  repetitions=3, full_output_equality=True, samples=samples, medians=summary,
                  compared_fields='All route fields including geometry, edge IDs, snaps, lengths; assessments and statuses',
                  seed_outputs=comparisons[0])
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
