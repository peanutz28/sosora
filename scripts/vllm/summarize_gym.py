"""Produce hosted-vs-vLLM tables from saved evidence, including failed attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def load_run(path):
    metrics = json.loads((path / 'metrics.json').read_text())
    rows = [json.loads(line) for line in (path / 'rollouts.jsonl').read_text().splitlines()]
    return metrics, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--new', required=True)
    parser.add_argument('--output', default='docs/GYM_RESULTS.md')
    args = parser.parse_args()
    old = Path('ml/nemo_gym/evidence/rollouts_2026-10-17')
    new = Path(args.new)
    lines = ['# NeMo Gym: hosted API versus Brev vLLM', '',
             'All scenarios are simulated. Same frozen tasks, policies, custom chat-completions',
             'runner and pinned official NeMo Gym tools/verifier; this is not the full Gym CLI.',
             'No weights were updated and no RL was performed. Both policies run on validation',
             'before either runs on test; test data does not tune the policy.', '',
             '| Serving | Split | Policy | Pass / requested | Provider errors | Mean request ms |',
             '|---|---|---|---:|---:|---:|']
    for label, root in [('Hosted NVIDIA API', old), ('Brev vLLM', new)]:
        for split in ['validation', 'test']:
            for policy in ['baseline', 'evidence_first']:
                path = root / f'{split}_{policy}'
                if not (path / 'metrics.json').exists():
                    lines.append(f'| {label} | {split} | {policy} | not measured | — | — |')
                    continue
                metrics, rows = load_run(path)
                passed = sum(row['reward'] == 1 for row in rows)
                latencies = [v for row in rows for v in row['request_latencies_ms']]
                latency = f'{statistics.mean(latencies):.1f}' if latencies else '—'
                lines.append(f"| {label} | {split} | {policy} | {passed}/{metrics['requested_limit']} | {metrics['error_count']} | {latency} |")
    lines += ['', 'Hosted results contain transport failures; they do not isolate policy quality.',
              'Serving comparisons also change checkpoint precision and backend defaults. The vLLM',
              'server disables thinking by default; the unmodified Gym runner has no per-request',
              'thinking flag. Server structural grammar is disabled for native tool parsing; frozen',
              'strict tool schemas are unchanged and HTTP tools/verifier validate arguments.',
              'Do not attribute all score changes to transport or call this RL.', '',
              '## Reproduce', '', '```sh',
              '# Export private LLM configuration and these existing runtime paths:',
              '# GYM_PYTHON, GYM_OFFICIAL, GYM_OUTPUT (fresh directory).',
              'bash scripts/vllm/run_gym.sh',
              f'python3 scripts/vllm/summarize_gym.py --new {new}', '```', '',
              f'New evidence: `{new}`. Each run saves rollout traces, metrics and configuration.',
              'Failed scenarios remain in the requested denominator; no selective retries.', '',
              '## Frozen task hashes', '']
    for split in ['validation', 'test']:
        path = Path('ml/nemo_gym/data') / f'{split}.jsonl'
        lines.append(f'- `{path}`: `{hashlib.sha256(path.read_bytes()).hexdigest()}`')
    Path(args.output).write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
