"""Offline checks for the roadmap ledger; NOT an authorization/security boundary."""
import argparse
import json
from pathlib import Path
import re
import sys

STATES = {'PROPOSED', 'ACCEPTED', 'IN_PROGRESS', 'REVIEW', 'DONE', 'BLOCKED', 'DEFERRED'}
RESULTS = {'PASS', 'FAIL', 'NOT_RUN', 'UNKNOWN', 'BLOCKED'}
PERMISSIONS = {'automatic_merge', 'release', 'real_model_benchmark', 'upstream_push', 'remote_protection_change'}
IDS = {f'D{i:02}' for i in range(23)}


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ['ledger must be an object']
    if data.get('version') != 1:
        errors.append('invalid version')
    if not re.fullmatch(r'[0-9a-f]{40}', str(data.get('main_commit', ''))):
        errors.append('invalid main commit')
    perms = data.get('permissions')
    if not isinstance(perms, dict) or set(perms) != PERMISSIONS or any(v is not False for v in perms.values()):
        errors.append('unapproved permission expansion')
    cards = data.get('cards')
    if not isinstance(cards, list) or any(not isinstance(c, dict) for c in cards):
        return errors + ['invalid cards']
    ids = [c.get('id') for c in cards]
    if any(not isinstance(i, str) for i in ids):
        return errors + ['invalid card ID']
    if set(ids) != IDS or len(ids) != len(IDS):
        errors.append('missing, duplicate or unknown card ID')
    by_id = {c.get('id'): c for c in cards}
    for card in cards:
        id = card.get('id')
        state = card.get('status')
        deps = card.get('depends')
        if not isinstance(state, str) or state not in STATES:
            errors.append(f'{id}: invalid state')
            continue
        if not isinstance(deps, list) or any(not isinstance(d, str) or d not in IDS or (id in IDS and d >= id) for d in deps) or len(set(deps)) != len(deps):
            errors.append(f'{id}: invalid dependency')
            continue
        if id in IDS and card.get('branch') != ('main' if id == 'D00' else f'dev/{id.lower()}'):
            errors.append(f'{id}: branch mismatch')
        if not isinstance(card.get('accepted'), bool) or not isinstance(card.get('merged'), bool):
            errors.append(f'{id}: missing acceptance flags')
        active = state in {'ACCEPTED', 'IN_PROGRESS', 'REVIEW', 'DONE'}
        if active and not str(card.get('approval') or '').strip():
            errors.append(f'{id}: missing approval')
        if active and any(by_id.get(d, {}).get('status') != 'DONE' or by_id.get(d, {}).get('merged') is not True for d in deps):
            errors.append(f'{id}: dependency not accepted and merged')
        checks = card.get('checks')
        if not isinstance(checks, list) or any(not isinstance(c, dict) or not isinstance(c.get('status'), str) or c['status'] not in RESULTS or not str(c.get('ref') or '').strip() or not str(c.get('name') or '').strip() for c in checks):
            errors.append(f'{id}: invalid evidence')
            continue
        if state in {'REVIEW', 'DONE'} and (type(card.get('pr')) is not int or card['pr'] <= 0 or not checks):
            errors.append(f'{id}: missing PR or checks')
        if state == 'DONE':
            if card.get('accepted') is not True or card.get('merged') is not True:
                errors.append(f'{id}: DONE without acceptance and merge')
            # A baseline observation can contain genuine failures. A separately
            # accepted baseline measurement requires PASS for the acceptance
            # check itself; retain negative observations in separate evidence.
            if not checks or any(c['status'] != 'PASS' for c in checks):
                errors.append(f'{id}: DONE has non-PASS acceptance check')
        elif card.get('accepted') is True or card.get('merged') is True:
            errors.append(f'{id}: non-DONE claims acceptance or merge')
        if state == 'PROPOSED' and (card.get('approval') is not None or card.get('pr') is not None or checks):
            errors.append(f'{id}: PROPOSED has implementation metadata')
    return errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument('ledger', type=Path)
    args = p.parse_args()
    try:
        data = json.loads(args.ledger.read_text(encoding='utf-8'))
        errors = validate(data)
    except (OSError, ValueError) as exc:
        errors = [type(exc).__name__]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('PASS: 23-card ledger structure, dependency and acceptance checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
