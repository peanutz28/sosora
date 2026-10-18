"""Check auth, model identity and a real structured tool call; save no secrets."""
import argparse
import json
import os
from pathlib import Path
import time

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--strict-native', action='store_true', help='Probe native auto parsing with strict=true, as used by Gym')
    args = parser.parse_args()
    base = os.environ['LLM_BASE_URL'].rstrip('/')
    model = os.environ['LLM_MODEL']
    headers = {'Authorization': 'Bearer ' + os.environ['LLM_API_KEY']}
    with httpx.Client(timeout=90) as client:
        unauth = client.get(base + '/models')
        response = client.get(base + '/models', headers=headers)
        response.raise_for_status()
        served = [m['id'] for m in response.json()['data']]
        start = time.perf_counter()
        response = client.post(base + '/chat/completions', headers=headers, json={
            'model': model, 'messages': [{'role': 'user', 'content': 'Call acknowledge with ok=true.'}],
            'tools': [{'type': 'function', 'function': {'name': 'acknowledge', 'description': 'Acknowledge a test.',
                       'strict': args.strict_native, 'parameters': {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False}}}],
            'tool_choice': 'auto' if args.strict_native else 'required', 'parallel_tool_calls': False,
            'temperature': 1., 'top_p': .95, 'max_tokens': 256,
            'chat_template_kwargs': {'enable_thinking': False}})
        elapsed = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        data = response.json()
        calls = data['choices'][0]['message'].get('tool_calls', [])
        valid = bool(calls and calls[0]['function']['name'] == 'acknowledge'
                     and json.loads(calls[0]['function']['arguments']) == {'ok': True})
        result = {'unauthenticated_models_status': unauth.status_code,
                  'authenticated_models_status': 200, 'served_model_ids': served,
                  'tool_call_valid': valid, 'strict_native_probe': args.strict_native, 'finish_reason': data['choices'][0].get('finish_reason'), 'latency_ms': elapsed, 'usage': data.get('usage'),
                  'tool_calls': calls, 'model': model}
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        if unauth.status_code != 401 or model not in served or not valid:
            raise SystemExit('Readiness/auth/tool-call validation failed')


if __name__ == '__main__':
    main()
