import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ['SOSORA_DB'] = str(Path(tempfile.mkdtemp(prefix='sosora-roads-')) / 'test.sqlite3')

from fastapi import HTTPException

from backend.road_network import Report, Segment, analyze_network, build_network, load_network
from backend import app as api


def segment(sid, u, v, name=None, lat=35.0, lng=-82.0):
    return Segment(sid, u, v, name or sid, 'residential', None, False, 120.0, lat, lng)


def network(edges, coords=None, access='A'):
    coords = coords or {}
    nodes = {}
    segments = {}
    for sid, u, v in edges:
        for node in (u, v):
            nodes.setdefault(node, coords.get(node, (35.0 + len(nodes) * 0.002, -82.5 + len(nodes) * 0.002)))
        mid_lat = (nodes[u][0] + nodes[v][0]) / 2
        mid_lng = (nodes[u][1] + nodes[v][1]) / 2
        segments[sid] = segment(sid, u, v, lat=mid_lat, lng=mid_lng)
    return build_network(segments, nodes, access_node=access)


def report(sid, condition, source='operator', verification='unverified', evidence='seen in the drill'):
    return Report(sid, condition, source, evidence, verification, '2026-10-17T00:00:00+00:00', '2026-10-17T00:00:00+00:00')


LOOP = [('ab', 'A', 'B'), ('ac', 'A', 'C'), ('bc', 'B', 'C'), ('cd', 'C', 'D'), ('de', 'D', 'E'), ('ce', 'C', 'E')]


class AnalysisTests(unittest.TestCase):
    def test_unknown_network_is_not_a_closure_map(self):
        result = analyze_network(network(LOOP), [], min_hinge_nodes=1)
        self.assertEqual([area['kind'] for area in result['areas'] if area['kind'] != 'uncertain_access'], [])
        self.assertTrue(any(area['dominant'] and area['evidence_basis'] == 'unknown_segments' for area in result['areas']))
        urgent_ids = {item['segment_id'] for item in result['urgent']}
        self.assertEqual(urgent_ids, {'ab', 'ac'})
        self.assertTrue(all(item['data_class'] == 'unknown' for item in result['urgent']))
        self.assertEqual(result['counts']['unknown'], 6)
        self.assertIn('No hurricane closure feed', result['disclaimer'])

    def test_one_block_creates_a_last_link_not_a_confirmed_cutoff(self):
        result = analyze_network(network(LOOP), [report('cd', 'blocked')], min_hinge_nodes=1)
        self.assertFalse(any(area['kind'] == 'blocked_off' for area in result['areas']))
        hinge = next(area for area in result['areas'] if area['kind'] == 'uncertain_link')
        self.assertEqual(hinge['hinge_segment_ids'], ['ce'])
        self.assertEqual(hinge['evidence_basis'], 'unknown_segments')
        self.assertGreaterEqual(hinge['node_count'], 2)
        reasons = {item['segment_id']: item['reason'] for item in result['urgent']}
        self.assertEqual(reasons['cd'], 'unverified_blockage')
        self.assertEqual(reasons['ce'], 'last_link')

    def test_blocking_every_exit_isolates_and_keeps_verification_distinct(self):
        unverified = analyze_network(
            network(LOOP),
            [report('cd', 'blocked'), report('ce', 'blocked')],
            min_hinge_nodes=1,
        )
        pocket = next(area for area in unverified['areas'] if area['kind'] == 'blocked_off')
        self.assertEqual(pocket['node_count'], 2)
        self.assertEqual(pocket['evidence_basis'], 'unverified_report')
        self.assertCountEqual(pocket['cut_segment_ids'], ['cd', 'ce'])
        cuts = [item for item in unverified['urgent'] if item['segment_id'] in {'cd', 'ce'}]
        self.assertEqual(sorted(item['segment_id'] for item in cuts), ['cd', 'ce'])
        self.assertTrue(all(item['reason'] == 'unverified_blockage' and item['priority'] == 'high' for item in cuts))

        verified = analyze_network(
            network(LOOP),
            [report('cd', 'blocked', verification='verified'), report('ce', 'blocked', verification='verified')],
            min_hinge_nodes=1,
        )
        pocket = next(area for area in verified['areas'] if area['kind'] == 'blocked_off')
        self.assertEqual(pocket['evidence_basis'], 'verified_blockage')
        self.assertFalse(any(item['segment_id'] in {'cd', 'ce'} for item in verified['urgent']))
        self.assertIn('not an official closure', pocket['summary'])

    def test_simulated_blockage_does_not_change_isolation(self):
        result = analyze_network(network(LOOP), [report('cd', 'blocked', source='simulation'), report('ce', 'blocked', source='simulation')], min_hinge_nodes=1)
        self.assertFalse(any(area['kind'] == 'blocked_off' for area in result['areas']))
        self.assertEqual(result['counts']['simulated'], 2)
        self.assertEqual(result['simulated_reports'][0]['data_class'], 'simulated')
        self.assertFalse(result['simulated_reports'][0]['applied_to_analysis'])

    def test_unverified_passable_corridor_is_labeled(self):
        result = analyze_network(network(LOOP), [report('ab', 'passable')], min_hinge_nodes=1)
        corridor = next(area for area in result['areas'] if area['kind'] == 'unverified_access')
        self.assertEqual(corridor['evidence_basis'], 'unverified_report')
        self.assertIn('ab', corridor['hinge_segment_ids'])
        match = next(item for item in result['urgent'] if item['segment_id'] == 'ab')
        self.assertEqual(match['reason'], 'unverified_passable')
        self.assertEqual(match['data_class'], 'unverified_report')

    def test_nearby_demo_incident_is_attached_without_calling_it_confirmed(self):
        coords = {'A': (35.60, -82.47), 'B': (35.60, -82.46), 'C': (35.601, -82.46), 'D': (35.61, -82.45), 'E': (35.611, -82.45)}
        incidents = [{'id': 'SOS-1', 'lat': 35.6102, 'lng': -82.4502, 'place': 'Bee Tree Road', 'people': 3, 'source': 'seeded_simulation'}]
        result = analyze_network(
            network(LOOP, coords),
            [report('cd', 'blocked'), report('ce', 'blocked')],
            incidents,
            min_hinge_nodes=1,
        )
        pocket = next(area for area in result['areas'] if area['kind'] == 'blocked_off')
        self.assertEqual(pocket['nearby_incidents'][0]['id'], 'SOS-1')
        self.assertEqual(pocket['nearby_incidents'][0]['data_class'], 'simulated')

    def test_swannanoa_extract_starts_fully_unknown(self):
        root = Path(__file__).resolve().parents[1]
        roads = load_network(root / 'frontend' / 'roads.geojson', root / 'swannanoa_roads.graphml')
        self.assertEqual(len(roads.segments), 1070)
        self.assertEqual(roads.component_count, 1)
        self.assertGreater(sum(1 for seg in roads.segments.values() if seg.name), 900)
        self.assertLess(roads.nodes[roads.access_node][1], -82.47)
        result = analyze_network(roads, [])
        self.assertFalse(any(area['kind'] == 'blocked_off' for area in result['areas']))
        self.assertGreaterEqual(len(result['urgent']), 1)
        self.assertLessEqual(len(result['urgent']), 12)
        self.assertTrue(all(item['data_class'] == 'unknown' for item in result['urgent']))
        named = '(169625258, 169505244, 0)'
        self.assertIn(named, roads.segments)
        blocked = analyze_network(roads, [report(named, 'blocked')])
        pocket = next(area for area in blocked['areas'] if area['kind'] == 'blocked_off')
        self.assertIn('(169505244, 169625258, 0)', pocket['cut_segment_ids'])
        self.assertEqual(pocket['evidence_basis'], 'unverified_report')
        self.assertTrue(any(item['segment_id'] == named and item['reason'] == 'unverified_blockage' for item in blocked['urgent']))


class ApiTests(unittest.TestCase):
    def setUp(self):
        with api.db() as con:
            con.execute('DELETE FROM road_reports')

    def test_state_keeps_incidents_and_adds_road_analysis(self):
        payload = api.state()
        self.assertGreaterEqual(len(payload['incidents']), 1)
        self.assertIn('route', payload)
        self.assertEqual(payload['route']['source'], 'simulated_graph')
        self.assertEqual(payload['road_reports'], [])
        self.assertEqual(payload['road_analysis']['counts']['unknown'], 1070)
        self.assertEqual(payload['road_analysis']['scenario']['data_class'], 'simulated')
        self.assertIsNone(payload['road_analysis']['scenario']['active_closure'])

    def test_report_persists_with_evidence_and_verification(self):
        sid = '(169625258, 169505244, 0)'
        saved = api.save_road_report(api.RoadReportIn(segment_id=sid, condition='blocked', source='operator', evidence='Water over the centerline.', verification='unverified'))
        self.assertEqual(saved['report']['data_class'], 'unverified_report')
        self.assertEqual(saved['report']['evidence'], 'Water over the centerline.')
        self.assertTrue(saved['report']['reported_at'])
        self.assertTrue(saved['report']['applied_to_analysis'])
        with sqlite3.connect(os.environ['SOSORA_DB']) as con:
            row = con.execute('SELECT source, evidence, verification, reported_at FROM road_reports WHERE segment_id=?', (sid,)).fetchone()
        self.assertEqual(row[0], 'operator')
        self.assertEqual(row[1], 'Water over the centerline.')
        self.assertEqual(row[2], 'unverified')
        self.assertTrue(row[3])
        analysis = api.road_analysis()
        self.assertTrue(any(item['segment_id'] == sid for item in analysis['urgent']))
        again = api.save_road_report(api.RoadReportIn(segment_id=sid, condition='blocked', source='operator', evidence='Crew confirmed the span is still under water.', verification='verified'))
        self.assertEqual(again['report']['reported_at'], saved['report']['reported_at'])
        self.assertEqual(again['report']['data_class'], 'verified')
        self.assertNotEqual(again['report']['updated_at'], '')
        verified = api.road_analysis()
        self.assertFalse(any(item['segment_id'] == sid for item in verified['urgent']))

    def test_validation_and_clear(self):
        sid = next(iter(api.ROAD_NETWORK.segments))
        with self.assertRaises(HTTPException) as verified:
            api.save_road_report(api.RoadReportIn(segment_id=sid, condition='passable', verification='verified', evidence='short'))
        self.assertEqual(verified.exception.status_code, 422)
        with self.assertRaises(HTTPException) as simulated:
            api.save_road_report(api.RoadReportIn(segment_id=sid, condition='blocked', source='simulation', verification='verified', evidence='This is only a drill note.'))
        self.assertEqual(simulated.exception.status_code, 422)
        with self.assertRaises(HTTPException) as missing:
            api.save_road_report(api.RoadReportIn(segment_id='(1, 2, 0)', condition='blocked'))
        self.assertEqual(missing.exception.status_code, 404)
        api.save_road_report(api.RoadReportIn(segment_id=sid, condition='passable', source='resident', evidence='Neighbor drove through.', verification='unverified'))
        cleared = api.save_road_report(api.RoadReportIn(segment_id=sid, condition='unknown'))
        self.assertTrue(cleared['cleared'])
        self.assertEqual(api.list_road_reports()['reports'], [])


if __name__ == '__main__':
    unittest.main()
