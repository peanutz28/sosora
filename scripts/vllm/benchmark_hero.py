"""Five real /api/radio requests through FastAPI with live ML + agent calls.

Run from repo root, with backend/ on PYTHONPATH, DEMO_MODE=false, and LLM vars.
No instance address or credential is written to evidence.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import statistics
import time

from fastapi.testclient import TestClient
from app.agent import RadioAgent
from app.factory import create_app
from app.routing import load_anchors, load_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--runs', type=int, default=5)
    args = parser.parse_args()
    if os.getenv('DEMO_MODE', 'true').lower() != 'false':
        raise SystemExit('This benchmark requires DEMO_MODE=false; no cached run is scored')
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Use a new output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    original = RadioAgent.completion
    turns = []

    async def measured(self, messages):
        start = time.perf_counter()
        row = {'turn': len(turns) + 1}
        try:
            result = await original(self, messages)
            row['tools'] = [c['function']['name'] for c in result.get('tool_calls') or []]
            return result
        except Exception as exc:
            row['error_type'] = type(exc).__name__
            raise
        finally:
            row['latency_ms'] = (time.perf_counter() - start) * 1000
            turns.append(row)

    RadioAgent.completion = measured
    app = create_app(load_graph(), load_anchors(), ':memory:')
    results = []
    try:
        with TestClient(app) as client:
            for index in range(args.runs):
                seed = client.post('/api/radio/demo/seed')
                seed.raise_for_status()
                seeded = seed.json()
                turns.clear()
                start = time.perf_counter()
                response = client.post('/api/radio', json={
                    'message': seeded['hero_message'], 'source_type': 'beacon',
                    'unit': 'beacon-ww-bridge', **seeded['beacon_position']})
                total_ms = (time.perf_counter() - start) * 1000
                response.raise_for_status()
                body = response.json()
                assessment = body.get('assessment', {})
                events = [e for e in app.state.engine.events if e['kind'].startswith('agent_')]
                incidents = body['state']['incidents']
                success = (body['parse'].get('parse_mode') == 'nemotron_lightning'
                           and len(assessment.get('affected_incident_ids', [])) == 5
                           and len([i for i in incidents if i.get('reachable') is False]) == 5
                           and not any(e['kind'] == 'agent_error' or e.get('call_id') == 'fallback' for e in events))
                row = {'run': index + 1, 'simulated_input': True, 'cached_llm': False,
                       'total_ms': total_ms, 'turns': list(turns), 'success': success,
                       'parse_mode': body['parse'].get('parse_mode'), 'assessment': assessment,
                       'closed_segment_ids': list(app.state.engine.closed_ids), 'events': events}
                results.append(row)
                output.write_text(json.dumps({'runs': results}, indent=2))
                print(json.dumps({k: row[k] for k in ('run', 'total_ms', 'success')}), flush=True)
    finally:
        RadioAgent.completion = original
    output.write_text(json.dumps({'runs': results, 'mean_total_ms': statistics.mean(r['total_ms'] for r in results),
                                  'all_successful': all(r['success'] for r in results)}, indent=2))


if __name__ == '__main__':
    main()
