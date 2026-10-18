"""Readiness checks; seed only after every dependency passes. Never print credentials."""
import asyncio
import json
import os
import sys
import httpx
import websockets

async def main():
    failed = False
    backend = os.environ['BACKEND_URL'].rstrip('/')
    base = os.environ.get('LLM_BASE_URL', '').rstrip('/')
    model = os.environ.get('LLM_MODEL', 'nvidia/nemotron-3.5-lightning-30b-a3b')
    headers = {'Authorization': 'Bearer ' + os.environ.get('LLM_API_KEY', '')}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        async def check(label, operation):
            nonlocal failed
            try:
                await operation()
                print('PASS ' + label, flush=True)
            except Exception as exc:
                failed = True
                # URLs/auth/error response bodies can contain secrets.
                print('FAIL ' + label + ' (' + type(exc).__name__ + ')', flush=True)
        async def get(url, predicate=lambda value: True, auth=None, is_json=True):
            response = await client.get(url, headers=auth)
            response.raise_for_status()
            assert predicate(response.json() if is_json else response.text)
        await check('vLLM health', lambda: get(base.removesuffix('/v1') + '/health', auth=headers, is_json=False))
        await check('vLLM model id: ' + model, lambda: get(base + '/models', lambda x: model in [m['id'] for m in x['data']], headers))
        await check('backend live mode and road graph', lambda: get(backend + '/health', lambda x: x['status'] == 'ok' and not x['demo_mode'] and x['graph_edges'] > 0))
        await check('frontend HTTP', lambda: get(os.environ['FRONTEND_URL'], lambda x: 'SOS' in x or 'sos' in x, is_json=False))
        await check('ASR ready tiny.en', lambda: get(os.environ['ASR_BASE_URL'].rstrip('/') + '/health', lambda x: x['status'] == 'ready' and x['model'] == 'tiny.en'))
        async def socket():
            async with websockets.connect(backend.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/events', open_timeout=10) as ws:
                message = json.loads(await asyncio.wait_for(ws.recv(), 10))
                assert message['type'] == 'state' and 'incidents' in message['state']
        await check('WebSocket initial state', socket)
        if failed:
            print('FAIL seed withheld: dependencies failed')
        else:
            async def seed():
                response = await client.post(backend + '/api/radio/demo/seed')
                response.raise_for_status()
                value = response.json()
                assert value['seeded'] == 9 and len(value['state']['incidents']) == 9
                assert all(i['reachable'] for i in value['state']['incidents'])
            await check('seed: 9 SOS reachable, 0 cut off', seed)
    return int(failed)

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
