import os
import unittest
from pathlib import Path

os.environ.setdefault('SOSORA_DB', str(Path('/tmp') / 'sosora-ops-test.sqlite3'))

from fastapi import HTTPException

from backend.ordering import priority_rank, sort_incidents
from backend.road_network import analyze_network
from backend import app as api
from tests.test_roads import network, report


class OrderingTests(unittest.TestCase):
    def test_priority_then_newest_and_unclassified_last(self):
        rows = [
            {'id': 'low-new', 'priority': 'low', 'created_at': '2024-09-27T15:00:00+00:00'},
            {'id': 'crit-old', 'priority': 'critical', 'created_at': '2024-09-27T10:00:00+00:00'},
            {'id': 'crit-new', 'priority': 'CRITICAL', 'created_at': '2024-09-27T12:00:00+00:00'},
            {'id': 'blank', 'priority': '', 'created_at': '2024-09-27T16:00:00+00:00'},
            {'id': 'odd', 'priority': 'unspecified', 'created_at': '2024-09-27T17:00:00+00:00'},
            {'id': 'high-missing', 'priority': 'high', 'created_at': None},
            {'id': 'high-old', 'priority': 'high', 'created_at': '2024-09-27T09:00:00+00:00'},
        ]
        ordered = [item['id'] for item in sort_incidents(rows, 'priority')]
        self.assertEqual(ordered[:2], ['crit-new', 'crit-old'])
        self.assertEqual(ordered[2:4], ['high-old', 'high-missing'])
        self.assertEqual(ordered[4], 'low-new')
        self.assertEqual(set(ordered[5:]), {'blank', 'odd'})
        self.assertEqual(priority_rank(None), 4)
        self.assertEqual(priority_rank('medium'), 2)
        newest = [item['id'] for item in sort_incidents(rows, 'newest')]
        self.assertEqual(newest[0], 'odd')
        self.assertIn('high-missing', newest[-2:])
        oldest = [item['id'] for item in sort_incidents(rows, 'oldest')]
        self.assertEqual(oldest[0], 'high-old')

    def test_api_sort_keeps_sos_contract(self):
        payload = api.list_incidents('priority')
        self.assertEqual(payload['priority_order'][-1], 'unclassified')
        ids = [item['id'] for item in payload['incidents']]
        self.assertIn('SOS-1042', ids)
        self.assertTrue(all(item['data_class'] in {'simulated', 'unverified_demo'} for item in payload['incidents']))
        self.assertTrue(all('created_at' in item for item in payload['incidents']))
        with self.assertRaises(HTTPException):
            api.list_incidents('random')


class RoadOpsTests(unittest.TestCase):
    def setUp(self):
        with api.db() as con:
            con.execute('DELETE FROM road_reports')
            con.execute('DELETE FROM road_report_history')

    def test_damaged_report_is_logged_and_duplicate_is_ignored(self):
        sid = '(169616818, 3315748552, 0)'
        saved = api.save_road_report(api.RoadReportIn(segment_id=sid, condition='damaged', source='operator', evidence='Mud and limbs across both lanes.', verification='unverified'))
        self.assertEqual(saved['report']['condition'], 'damaged')
        self.assertTrue(saved['report']['applied_to_analysis'])
        again = api.save_road_report(api.RoadReportIn(segment_id=sid, condition='damaged', source='operator', evidence='Mud and limbs across both lanes.', verification='unverified'))
        self.assertTrue(again['duplicate'])
        with api.db() as con:
            history = con.execute('SELECT COUNT(*) FROM road_report_history WHERE segment_id=?', (sid,)).fetchone()[0]
        self.assertEqual(history, 1)
        state = api.state()
        self.assertTrue(any('ROAD' in event['message'] for event in state['events']))
        self.assertIn('created_at', state['incidents'][0])

    def test_blockage_applies_to_the_opposite_osm_edge(self):
        edges = [('(1, 2, 0)', 1, 2), ('(2, 1, 0)', 2, 1), ('(2, 3, 0)', 2, 3), ('(3, 2, 0)', 3, 2)]
        open_road = analyze_network(network(edges, access=1), [report('(2, 3, 0)', 'blocked')])
        pocket = next(area for area in open_road['areas'] if area['kind'] == 'blocked_off')
        self.assertIn('(3, 2, 0)', pocket['cut_segment_ids'])
        self.assertEqual(pocket['evidence_basis'], 'unverified_report')
        self.assertIn('unverified report', pocket['summary'])

    def test_simulated_blocks_stay_labeled_when_the_drill_applies_them(self):
        quiet = analyze_network(network([('ab', 'A', 'B'), ('ac', 'A', 'C'), ('bc', 'B', 'C'), ('cd', 'C', 'D'), ('de', 'D', 'E'), ('ce', 'C', 'E')]), [report('cd', 'blocked', source='simulation'), report('ce', 'blocked', source='simulation')], min_hinge_nodes=1)
        self.assertFalse(any(area['kind'] == 'blocked_off' for area in quiet['areas']))
        applied = analyze_network(network([('ab', 'A', 'B'), ('ac', 'A', 'C'), ('bc', 'B', 'C'), ('cd', 'C', 'D'), ('de', 'D', 'E'), ('ce', 'C', 'E')]), [report('cd', 'blocked', source='simulation'), report('ce', 'blocked', source='simulation')], min_hinge_nodes=1, apply_simulated=True)
        pocket = next(area for area in applied['areas'] if area['kind'] == 'blocked_off')
        self.assertEqual(pocket['evidence_basis'], 'simulated')
        self.assertTrue(applied['simulation_applied'])

    def test_reset_is_idempotent_and_keeps_non_demo_incidents(self):
        with api.db() as con:
            con.execute(
                "INSERT OR IGNORE INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ('SOS-KEEP', 'high', 'resident drill', 'Bee Tree Road', 1, 35.61, -82.43, 'Received', 'Keep this resident demo row.', '2026-10-17T00:00:00+00:00', 'resident_demo', 'sos'),
            )
        first = api.demo_reset()
        second = api.demo_reset()
        first_ids = sorted(item['id'] for item in first['incidents'])
        second_ids = sorted(item['id'] for item in second['incidents'])
        self.assertEqual(first_ids, second_ids)
        self.assertIn('SOS-KEEP', second_ids)
        self.assertTrue(any(item['id'] == 'SOS-1042' and item['place'] == 'Warren Wilson Road' and item['data_class'] == 'simulated' for item in second['incidents']))
        self.assertTrue(second['road_analysis']['simulation_applied'])
        self.assertTrue(any(report['source'] == 'simulation' for report in second['road_reports']))
