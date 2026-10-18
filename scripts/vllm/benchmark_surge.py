"""Real ML parse throughput: 100 sequential and 100 concurrent requests.

Only simulated fixture text is sent. Requires the ML server itself to be running
with DEMO_MODE=false and the private vLLM configuration. Failures are retained.
"""
import argparse
import asyncio
import json
import math
from pathlib import Path
import time

import httpx
from ml.inference.radio import DEMO_FIXTURES


def percentile(values, p):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * p) - 1)] if values else None


async def batch(base, count, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    async with httpx.AsyncClient(timeout=180, limits=httpx.Limits(max_connections=100, max_keepalive_connections=100)) as client:
        async def request(index):
            async with semaphore:
                start = time.perf_counter()
                status, error = None, None
                try:
                    response = await client.post(base.rstrip('/') + '/ml/radio/parse', json={
                        'message': DEMO_FIXTURES[index % len(DEMO_FIXTURES)]['message'],
                        'received_at': '2026-10-17T23:00:00-04:00', 'channel': 'radio'})
                    status = response.status_code
                    response.raise_for_status()
                    if response.json().get('raw') != DEMO_FIXTURES[index % len(DEMO_FIXTURES)]['message']:
                        error = 'InvalidParse'
                except (httpx.HTTPError, ValueError) as exc:
                    error = type(exc).__name__
                results.append({'index': index, 'status': status, 'error_type': error,
                                'latency_ms': (time.perf_counter() - start) * 1000})
        start = time.perf_counter()
        await asyncio.gather(*(request(i) for i in range(count)))
        elapsed = time.perf_counter() - start
    successful = [r for r in results if r['error_type'] is None]
    latencies = [r['latency_ms'] for r in results]
    return {'concurrency': concurrency, 'requests': count, 'successes': len(successful),
            'elapsed_seconds': elapsed, 'successful_messages_per_second': len(successful) / elapsed,
            'p50_ms_all_attempts': percentile(latencies, .5), 'p95_ms_all_attempts': percentile(latencies, .95),
            'attempts': sorted(results, key=lambda r: r['index'])}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ml-base', default='http://127.0.0.1:18002')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = Path(args.output)
    if path.exists():
        raise SystemExit('Use a new output file')
    result = {'simulated_input': True, 'cached_llm': False, 'batches': []}
    for concurrency in (1, 100):
        row = await batch(args.ml_base, 100, concurrency)
        result['batches'].append(row)
        path.write_text(json.dumps(result, indent=2))
        print(json.dumps({k: v for k, v in row.items() if k != 'attempts'}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
