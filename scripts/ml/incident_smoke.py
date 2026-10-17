"""Opt-in real provider smoke test. Never supplies a fallback or fabricated response."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi import HTTPException
from ml.inference.incident import IncidentRequest, ExplainRequest, parse, explain, llm_configuration
from scripts.ml.run_native_api import load_provider_settings

async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', help='Report to parse through the configured real provider')
    parser.add_argument('--explain-json', type=Path, help='JSON file matching ExplainRequest')
    parser.add_argument('--env-file', type=Path, help='Private local provider settings; never executed as shell code')
    args = parser.parse_args()
    if bool(args.report) == bool(args.explain_json):
        parser.error('Choose exactly one of --report or --explain-json')
    if args.env_file:
        try:
            load_provider_settings(args.env_file)
        except (OSError, ValueError):
            print('Invalid private settings file; no result produced.', file=sys.stderr)
            return 2
    config = llm_configuration()
    if not config['configured']:
        print('Unavailable: ' + config['configuration_error'], file=sys.stderr)
        return 2
    try:
        result = (await parse(IncidentRequest(report=args.report)) if args.report else
                  await explain(ExplainRequest.model_validate_json(args.explain_json.read_text())))
    except HTTPException as exc:
        print(f'Provider request failed (HTTP {exc.status_code}); no result produced.', file=sys.stderr)
        return 1
    except (ValueError, OSError):
        print('Invalid input; no result produced.', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
