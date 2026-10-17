"""Integrity checks for the preserved, simulated live evaluation evidence."""
import hashlib
import json
from pathlib import Path
import unittest

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[3]


class EvidenceIntegrityTests(unittest.TestCase):
    def test_complete_unique_scenario_coverage_and_metrics(self):
        manifest = json.loads((EVIDENCE / 'manifest.json').read_text())
        self.assertEqual([(r['split'], r['policy'], r['exit_code']) for r in manifest['runs']],
                         [(s, p, 0) for s in ('validation', 'test') for p in ('baseline', 'evidence_first')])
        for run in manifest['runs']:
            split, policy = run['split'], run['policy']
            catalog = [json.loads(line) for line in (ROOT / f'ml/nemo_gym/data/{split}.jsonl').read_text().splitlines()]
            folder = EVIDENCE / f'{split}_{policy}'
            rows = [json.loads(line) for line in (folder / 'rollouts.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 14)
            self.assertEqual({r['scenario_id'] for r in rows}, {r['scenario_id'] for r in catalog})
            metrics = json.loads((folder / 'metrics.json').read_text())
            self.assertEqual(metrics['scenarios_completed'], 14)
            self.assertAlmostEqual(metrics['mean_reward'], sum(r['reward'] for r in rows) / 14)
            self.assertEqual(metrics['error_count'], sum(r['error_type'] is not None for r in rows))
            self.assertEqual(metrics['model'], 'nvidia/nemotron-3.5-lightning-30b-a3b')
            self.assertFalse(metrics['improvement_claim'])

    def test_inputs_unchanged(self):
        manifest = json.loads((EVIDENCE / 'manifest.json').read_text())
        for name, digest in manifest['input_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)


if __name__ == '__main__':
    unittest.main()
