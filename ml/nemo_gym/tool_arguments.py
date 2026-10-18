"""Opt-in native-tool compatibility; never repairs rescue decisions.

Qwen XML parameters arrive as text. Preserve strings where the schema allows
them; only decode null spellings for a nullable scalar that forbids strings.
The runner records both representations and still uses the original verifier.
"""
import json


ADAPTER = 'nullable-null-v1'


def adapt_arguments(arguments, parameters):
    """Return (JSON arguments, edits), without mutating input or filling fields."""
    try:
        parsed = json.loads(arguments)
    except (ValueError, TypeError):
        return arguments, []
    if not isinstance(parsed, dict):
        return arguments, []
    edits = []
    for name, schema in parameters.get('properties', {}).items():
        # Deliberately support only the exact scalar-union schema we can prove
        # unambiguous. Unknown schemas and string|null unions pass unchanged.
        variants = schema.get('anyOf', [])
        types = [variant.get('type') for variant in variants]
        if len(types) != 2 or 'null' not in types:
            continue
        if set(types) not in ({'integer', 'null'}, {'number', 'null'}, {'boolean', 'null'}):
            continue
        if isinstance(parsed.get(name), str) and parsed[name] in {'None', 'null'}:
            edits.append({'field': name, 'before': parsed[name], 'after': None})
            parsed[name] = None
    return (json.dumps(parsed) if edits else arguments), edits
