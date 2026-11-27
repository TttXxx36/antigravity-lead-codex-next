"""Offline, deterministic Codex CLI double. No network or external commands."""
import json
import os
from pathlib import Path
import sys


def main():
    args = sys.argv[1:]
    if args == ['--version']:
        print('codex-cli 0.170.0 (mock)')
        return 0
    if not args or args[0] != 'exec' or '-o' not in args or '--json' not in args:
        return 2
    if any('network_access=true' in arg or 'danger-full-access' in arg for arg in args):
        return 2
    prompt = sys.stdin.read()
    if not prompt.strip():
        return 2
    case = os.environ.get('ALC_MOCK_CASE', 'B01')
    cwd = Path(args[args.index('-C') + 1]) if '-C' in args else Path.cwd()
    resume = len(args) > 1 and args[1] == 'resume'
    failed = case == 'B04'
    files = [] if failed else ['answer.txt'] + (['second.txt'] if case == 'B02' else [])
    for name in files:
        (cwd / name).write_text('mock resume\n' if resume else 'mock result\n', encoding='utf-8')
    report = dict(status='failed' if failed else 'completed', summary='synthetic error' if failed else 'synthetic result', files_modified=files, commands_run=[], verification_passed=False, risks_or_followups=['mock only; checks not run'], notes_for_orchestrator='')
    if '--output-schema' in args and Path(args[args.index('--output-schema')+1]).name == 'report_schema_v2.json':
        report = dict(version=2,status=report['status'],summary=report['summary'],risks=['mock only; checks not run'],blockers=['synthetic failure'] if failed else [],verification_claim='not_run')
    Path(args[args.index('-o') + 1]).write_text(json.dumps(report), encoding='utf-8')
    print(json.dumps({'type': 'thread.started', 'thread_id': 'mock-thread-01'}))
    if failed:
        print(json.dumps({'type': 'error', 'message': 'synthetic error'}))
    print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(report)}}))
    # Deliberately omit usage: no real model was called; no fabricated token totals.
    print(json.dumps({'type': 'turn.failed' if failed else 'turn.completed'}))
    return 7 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
