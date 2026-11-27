"""D01 fixed dispatcher contract, mock routing/CLI only; not a full product test."""
import argparse
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from types import ModuleType
from typing import Any, Iterator
from unittest.mock import patch
import uuid
from run_benchmark import DISPATCH, MOCK, SUITE, isolated_env, init_git, summarize

BASELINE_SOURCE = '2057553f544c0ef605eb2c9ad8ae0f8fb59df84a'
SOURCE = '512528b48df454313abec9ee422a21c4bd8ca8e8'
PARTS = ('71ceae90ea5a4b5df6079813533ae123eba7f7d3', '954c03bf4c26766cd5fde98df0985b5e70b4778c', 'd3cd17225d860441aa1b8ac10b021b699e9d1808')


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def load(home, excerpts):
    if excerpts is None:
        raw = DISPATCH.read_bytes()
        if SOURCE not in (blob(raw), blob(raw.replace(b'\r\n', b'\n'))):
            raise ValueError('dispatcher differs from pinned repair candidate')
        spec = importlib.util.spec_from_file_location('d01_contract', DISPATCH)
        d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(d)
    else:
        import fcntl
        d = ModuleType('d01_excerpt')
        d.__dict__.update(argparse=argparse, contextlib=contextlib, datetime=datetime, timezone=timezone, fcntl=fcntl, json=json, os=os, re=re, shutil=shutil, subprocess=subprocess, sys=sys, uuid=uuid, Path=Path, Any=Any, Iterator=Iterator)
        for i, expected in enumerate(PARTS):
            raw = (excerpts / f'part{i}.py').read_bytes()
            if blob(raw) != expected:
                raise ValueError('excerpt SHA mismatch')
            exec(compile(raw, f'upstream-part{i}', 'exec'), d.__dict__)
        d.get_codex_bin = lambda: None
        d.resolve_model_and_effort = lambda **kw: None
    d.STATE_DIR = home / '状态 空格'
    d.STATE_FILE = d.STATE_DIR / 'state.json'
    d.LOCK_FILE = d.STATE_DIR / 'state.lock'
    d.RUNS_DIR = d.STATE_DIR / 'runs'
    d.WORKTREES_DIR = d.STATE_DIR / 'worktrees'
    d.SCHEMA_PATH = home / 'mock-schema.json'
    d.SCHEMA_PATH.write_text('{}', encoding='utf-8')
    return d


def probe(case, excerpts):
    start = time.perf_counter()
    row = dict(case=case['id'], status='PASS', detail=None, payload_bytes=None, real_model_calls=0, usage_source='unknown', input_tokens=None, output_tokens=None)
    try:
        with tempfile.TemporaryDirectory(prefix='alc-contract-') as tmp:
            home = Path(tmp)
            env = isolated_env(home)
            with patch.dict(os.environ, env, clear=True):
                d = load(home, excerpts)
                cwd = home / '中文 空格'; cwd.mkdir(); init_git(cwd, env)
                original = d.run_subprocess_with_timeout
                calls = []
                def boundary(cmd, **kw):
                    if cmd[0] != 'D01_MOCK_ONLY' or cmd[1] != 'exec' or any('network_access=true' in x or 'danger-full-access' in x for x in cmd):
                        raise RuntimeError('refused unexpected command')
                    calls.append(cmd[2] == 'resume')
                    kw['env'] = dict(env, ALC_MOCK_CASE=case['id'])
                    return original([sys.executable, '-I', str(MOCK), *cmd[1:]], **kw)
                def once(n):
                    return d.execute_single_task(prompt=case['prompt'], cwd=cwd, backend='codex', difficulty='low', model='mock-model', effort='low', quality='balanced', alternate=False, prefer_wide=False, sandbox='workspace-write', network=False, isolation='worktree', timeout=20, files_hint=None, task_id=f'd01-{n}', dry_run=False)
                route = dict(model='mock-model', effort='low', effective_difficulty='low')
                with patch.object(d, 'get_codex_bin', return_value='D01_MOCK_ONLY'), patch.object(d, 'resolve_model_and_effort', return_value=route), patch.object(d, 'run_subprocess_with_timeout', side_effect=boundary):
                    if case['id'] == 'B07':
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            results = list(pool.map(once, [1, 2]))
                        assert results[0]['workdir'] != results[1]['workdir'] and results[0]['branch'] != results[1]['branch']
                    elif case['id'] == 'B04':
                        results = [once(1), once(2)]
                    else:
                        results = [once(1)]
                    for result in results:
                        report = result['report']; worktree = Path(result['workdir'])
                        assert report['status'] == case['expected']
                        assert result['exit_code'] == (7 if case['id'] == 'B04' else 0)
                        assert result['usage'] is None and report['verification_passed'] is False
                        assert result['session_id'] == 'mock-thread-01' and not result['timed_out']
                        assert result['git_truth']['is_git'] and not result['git_truth']['has_new_commits']
                        assert worktree.is_relative_to(d.WORKTREES_DIR)
                        if case['id'] == 'B04':
                            assert not (worktree / 'answer.txt').exists() and report['summary'] == 'synthetic error'
                        else:
                            assert (worktree / 'answer.txt').read_text(encoding='utf-8') == 'mock result\n'
                            if case['id'] == 'B02':
                                assert (worktree / 'second.txt').read_text(encoding='utf-8') == 'mock result\n'
                    if case['id'] == 'B03':
                        args = argparse.Namespace(task_id='d01-1', prompt='Update answer.txt', backend=None, session_id=None, cwd=None, sandbox=None, network=False, model=None, effort=None, difficulty='auto', prefer_wide=False, quality='smart', alternate=None, dry_run=False, timeout=20)
                        buf = io.StringIO()
                        with contextlib.redirect_stdout(buf):
                            assert d.cmd_resume(args) == 0
                        resumed = json.loads(buf.getvalue())
                        assert resumed['session_id'] == results[0]['session_id'] and resumed['usage'] is None
                        assert (Path(results[0]['workdir']) / 'answer.txt').read_text(encoding='utf-8') == 'mock resume\n'
                        results.append(resumed)
                        assert calls == [False, True]
                    state = json.loads(d.STATE_FILE.read_text(encoding='utf-8'))['tasks']
                    assert len(state) == (2 if case['id'] in ('B04', 'B07') else 1)
                    assert all(t['status'] == case['expected'] and not t['network'] for t in state.values())
                    assert not (cwd / 'answer.txt').exists() and not (cwd / 'second.txt').exists()
                    assert len(calls) == len(results)
                    row['payload_bytes'] = sum((Path(x['run_dir']) / 'events.jsonl').stat().st_size for x in results)
                    row['mock_processes'] = len(calls)
    except (FileNotFoundError, ImportError) as exc:
        row.update(status='NOT_RUN', detail=type(exc).__name__)
    except Exception as exc:
        row.update(status='FAIL', detail=type(exc).__name__)
    row['latency_ms'] = round((time.perf_counter() - start) * 1000, 3)
    return row


def observations(excerpts):
    with tempfile.TemporaryDirectory(prefix='alc-observe-') as tmp:
        home = Path(tmp)
        with patch.dict(os.environ, isolated_env(home), clear=True):
            d = load(home, excerpts)
            missing = d.parse_report_file(home / 'missing.json', None, '', 0)
            contradiction = d.parse_report_file(home / 'missing.json', '{"status":"completed","summary":"synthetic"}', '', 7)
            d.ensure_state_dirs(); d.STATE_FILE.write_text('{broken', encoding='utf-8')
            with d.locked_state() as state:
                state['tasks']['synthetic'] = {'status': 'completed'}
            return dict(missing_report_exit0=dict(status=missing['status'], verification_passed=missing['verification_passed']), nonzero_exit_completed_report=dict(status=contradiction['status']), corrupt_state_overwritten='synthetic' in json.loads(d.STATE_FILE.read_text(encoding='utf-8'))['tasks'])


def main():
    if not __debug__:
        raise SystemExit('assertions required')
    p = argparse.ArgumentParser(); p.add_argument('--excerpt-dir', type=Path); p.add_argument('--repeat', type=int, default=5); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if not 1 <= args.repeat <= 100:
        p.error('repeat must be 1..100')
    cases = [c for c in SUITE['cases'] if c['id'] not in ('B05', 'B06')]
    rows = [probe(c, args.excerpt_dir) for c in cases for _ in range(args.repeat)]
    groups = [dict(case=c['id'], counts={s:sum(r['case']==c['id'] and r['status']==s for r in rows) for s in ('PASS','FAIL','NOT_RUN')}, latency=summarize([r['latency_ms'] for r in rows if r['case']==c['id'] and r['status']=='PASS'])) for c in cases]
    try:
        obs = observations(args.excerpt_dir)
    except (FileNotFoundError, ImportError, ValueError) as exc:
        obs = dict(status='NOT_RUN', detail=type(exc).__name__)
    result = dict(mode='verified-excerpts' if args.excerpt_dir else 'candidate-full-module-fixed-routing', baseline_commit=SUITE['baseline_commit'], upstream_source_blob=BASELINE_SOURCE, tested_source_blob=BASELINE_SOURCE if args.excerpt_dir else SOURCE, excerpt_blobs=list(PARTS) if args.excerpt_dir else [], platform=platform.system(), python=platform.python_version(), repeat=args.repeat, samples=rows, groups=groups, baseline_observations=obs, mock_processes=sum(r.get('mock_processes', 0) for r in rows), real_model_calls=0)
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('mode','groups','baseline_observations','mock_processes','real_model_calls')}, indent=2))
    return 1 if any(r['status']!='PASS' for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
