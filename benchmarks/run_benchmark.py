"""Local-only D01 runner. Default probes actual upstream through a CLI double.
--harness-only checks the double and metrics, NOT upstream performance.
"""
import argparse
import contextlib
import hashlib
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import queue
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / 'benchmarks/task_suite.json').read_text(encoding='utf-8'))
MOCK = ROOT / 'tests/mock_codex.py'
DISPATCH = ROOT / 'skills/multi-agent-dispatch/scripts/dispatch.py'
SERVER = ROOT / 'plugins/codex-console/server/index.mjs'
DISPATCH_FILES = {
    'skills/multi-agent-dispatch/scripts/dispatch.py': '512528b48df454313abec9ee422a21c4bd8ca8e8',
    'skills/multi-agent-dispatch/resources/report_schema.json': '36d5a817785eeaf04a972c5c363ab04beb5c482e',
}
MCP_FILES = {
    'plugins/codex-console/server/index.mjs': '4eadeaa1c669162f3727d1498fa5f7bca90763d5',
    'plugins/codex-console/server/runner.mjs': '40ea4cecd5eb36d0005678ae001476dd9817276f',
    'plugins/codex-console/server/codex-store.mjs': '25b9a0a0fdb766805a7686fa5144cea0a4243b80',
    'plugins/codex-console/server/console-db.mjs': 'bdbd08cf975ff8f2ba51a8241613750607f0ff4f',
    'plugins/codex-console/server/quota.mjs': '2c8b6302fb6607d94c3c3d0a6b607e2b4b24b409',
    'plugins/codex-console/package.json': '993f605304dfa4148028dac582f2bdbbc8b1befe',
    'plugins/codex-console/package-lock.json': '489de3cc311ff985f960aa09a70b0fbb8c8dcab4',
}


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def verify_sources(pins):
    for rel, expected in pins.items():
        raw = (ROOT / rel).read_bytes()
        if expected not in (blob_sha(raw), blob_sha(raw.replace(b'\r\n', b'\n'))):
            raise ValueError('source differs from fixed baseline: ' + rel)


def checkout_sha():
    try:
        p = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def run(cmd, *, cwd, env, input=None, timeout=30):
    return subprocess.run(cmd, cwd=cwd, env=env, input=input, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', timeout=timeout)


def isolated_env(home):
    # No inherited provider credentials, Git config, proxy or custom startup hooks.
    keys = ('PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP')
    env = {k: os.environ[k] for k in keys if k in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / 'codex'),
               AGY_DISPATCH_STATE_DIR=str(home / 'dispatch'), AGY_MODELS_CACHE_FILE=str(home / 'empty-models.json'),
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0',
               PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    (home / 'empty-models.json').write_text('{}', encoding='utf-8')
    return env


def summarize(values):
    values = sorted(values)
    if not values:
        return None
    return {'median_ms': round(statistics.median(values), 3),
            'p95_ms': round(values[math.ceil(.95 * len(values)) - 1], 3)}


def mock_run(case, cwd, env, resume=False):
    report = cwd / ('resume.json' if resume else 'report.json')
    args = ['exec'] + (['resume', 'mock-thread-01'] if resume else ['-C', str(cwd)])
    p = run([sys.executable, str(MOCK), *args, '--json', '-o', str(report), '-'],
            cwd=cwd, env=dict(env, ALC_MOCK_CASE=case['id']), input=case['prompt'])
    result = json.loads(report.read_text(encoding='utf-8'))
    return p.returncode, result, len(p.stdout.encode('utf-8'))


def init_git(cwd, env):
    git = shutil.which('git')
    if not git:
        raise RuntimeError('Git unavailable')
    (cwd / 'seed.txt').write_text('baseline\n', encoding='utf-8')
    for args in (['init', '-q'], ['add', 'seed.txt'], ['-c', 'user.name=Mock', '-c', 'user.email=mock@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'seed']):
        if run([git, *args], cwd=cwd, env=env).returncode:
            raise RuntimeError('synthetic Git setup failed')


def fixture_db(home):
    dest = home / 'codex'
    dest.mkdir()
    schema = {
        'state_5': '''CREATE TABLE projects (id TEXT, name TEXT, position INTEGER); CREATE TABLE project_roots (project_id TEXT, path TEXT); CREATE TABLE thread_spawn_edges (parent_thread_id TEXT, child_thread_id TEXT, status TEXT); CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, created_at INTEGER, updated_at INTEGER, created_at_ms INTEGER, updated_at_ms INTEGER, source TEXT, thread_source TEXT, originator TEXT, cwd TEXT, title TEXT, name TEXT, preview TEXT, tokens_used INTEGER, archived INTEGER, is_pinned INTEGER, git_branch TEXT, git_sha TEXT, model TEXT, reasoning_effort TEXT, agent_nickname TEXT, agent_role TEXT, agent_path TEXT, project_id TEXT, history_mode TEXT);''',
        'goals_1': 'CREATE TABLE thread_goals (thread_id TEXT, goal_id TEXT, objective TEXT, status TEXT, token_budget INTEGER, tokens_used INTEGER, time_used_seconds INTEGER, updated_at_ms INTEGER);',
        'queue_1': 'CREATE TABLE queued_items (id TEXT, thread_id TEXT, payload_json TEXT, queue_order INTEGER, created_at_ms INTEGER);',
        'thread_history_1': 'CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, rollout_ordinal INTEGER, status TEXT, error_json TEXT, started_at INTEGER, completed_at INTEGER, duration_ms INTEGER); CREATE TABLE thread_items (thread_id TEXT, turn_id TEXT, item_id TEXT, rollout_ordinal INTEGER, created_at_ms INTEGER, item_type TEXT, item_json TEXT);'
    }
    for name, sql in schema.items():
        with contextlib.closing(sqlite3.connect(dest / (name + '.sqlite'))) as db:
            db.executescript(sql)
            if name == 'state_5':
                db.execute('INSERT INTO threads (id,created_at,updated_at,source,thread_source,cwd,title,preview,tokens_used,archived,is_pinned) VALUES (?,?,?,?,?,?,?,?,?,?,?)', ('fixture-thread-01', 1700000000, 1700000001, 'exec', 'user', str(home), 'fixture', 'synthetic', 0, 0, 0))
            if name == 'thread_history_1':
                db.execute('INSERT INTO thread_items VALUES (?,?,?,?,?,?,?)', ('fixture-thread-01', 'turn-1', 'item-1', 1, 1700000001000, 'agentMessage', '{"text":"synthetic"}'))
            db.commit()


def mcp_probe(case, home, env, warm):
    node = shutil.which('node')
    if not node or not SERVER.is_file() or not (SERVER.parent.parent / 'node_modules/@modelcontextprotocol/sdk').is_dir():
        raise FileNotFoundError('Node/server dependencies unavailable; no install attempted')
    verify_sources(MCP_FILES)
    fixture_db(home)
    # A real Codex executable is never passed. The Python executable cannot run app-server.
    child = subprocess.Popen([node, '--no-warnings', str(SERVER), '--data-dir', str(home / 'plugin')], cwd=home,
                             env=dict(env, CODEX_BIN=sys.executable), stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    inbox = queue.Queue()
    def read():
        for line in child.stdout:
            inbox.put(line)
        inbox.put(None)
    threading.Thread(target=read, daemon=True).start()
    def rpc(i, method, params):
        msg = json.dumps({'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params}).encode() + b'\n'
        child.stdin.write(msg); child.stdin.flush()
        deadline = time.monotonic() + 10
        while True:
            line = inbox.get(timeout=max(.001, deadline - time.monotonic()))
            if line is None:
                raise RuntimeError('MCP process closed')
            result = json.loads(line)
            if result.get('id') == i:
                if 'error' in result or result.get('result', {}).get('isError'):
                    raise RuntimeError('MCP RPC error')
                return result['result'], len(line)
    try:
        rpc(1, 'initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'd01', 'version': '1'}})
        child.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'); child.stdin.flush()
        name, args = ('list_codex_tasks', {'limit': 10}) if case['id'] == 'B05' else ('get_codex_task_detail', {'threadId': 'fixture-thread-01'})
        params = {'name': name, 'arguments': args}
        if warm:
            rpc(2, 'tools/call', params)
        start = time.perf_counter()
        out, size = rpc(3, 'tools/call', params)
        sc = out.get('structuredContent', {})
        if case['id'] == 'B05':
            assert any(t['id'] == 'fixture-thread-01' for t in sc['tasks'])
        else:
            assert sc['task']['id'] == 'fixture-thread-01' and sc['messages']
        return size, (time.perf_counter() - start) * 1000
    finally:
        child.kill(); child.wait(timeout=10)
        child.stdin.close(); child.stdout.close()


def dispatch_probe(case, home, env):
    verify_sources(DISPATCH_FILES)
    with patch.dict(os.environ, env, clear=True):
        spec = importlib.util.spec_from_file_location('d01_dispatch', DISPATCH)
        d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(d)
        cwd = home / '中文 空格'; cwd.mkdir(); init_git(cwd, env)
        original = d.run_subprocess_with_timeout
        def mock_boundary(cmd, **kwargs):
            if cmd[0] != 'D01_MOCK_ONLY' or 'exec' not in cmd or any('network_access=true' in x or 'danger-full-access' in x for x in cmd):
                raise RuntimeError('unexpected CLI invocation; refused')
            kwargs['env'] = dict(env, ALC_MOCK_CASE=case['id'])
            return original([sys.executable, '-I', str(MOCK), *cmd[1:]], **kwargs)
        def once(n):
            return d.execute_single_task(prompt=case['prompt'], cwd=cwd, backend='codex', difficulty='low', model='mock-model', effort='low', quality='balanced', alternate=False, prefer_wide=False, sandbox='workspace-write', network=False, isolation='worktree', timeout=20, files_hint=None, task_id='d01-' + str(n), dry_run=False)
        with patch.object(d, 'get_codex_bin', return_value='D01_MOCK_ONLY'), patch.object(d, 'run_subprocess_with_timeout', side_effect=mock_boundary):
            if case['id'] == 'B07':
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(once, [1, 2]))
                assert results[0]['workdir'] != results[1]['workdir']
                assert results[0]['branch'] != results[1]['branch']
            elif case['id'] == 'B04':
                results = [once(1), once(2)]
            else:
                results = [once(1)]
            for result in results:
                assert result['report']['status'] == case['expected']
                assert (result['exit_code'] == 0) == (case['expected'] == 'completed')
                assert result['usage'] is None
                assert result['report']['verification_passed'] is False
                if case['expected'] == 'completed':
                    assert (Path(result['workdir']) / 'answer.txt').read_text(encoding='utf-8') == 'mock result\n'
                    if case['id'] == 'B02':
                        assert (Path(result['workdir']) / 'second.txt').read_text(encoding='utf-8') == 'mock result\n'
                else:
                    assert not (Path(result['workdir']) / 'answer.txt').exists()
            if case['id'] == 'B03':
                buf = io.StringIO()
                args = d.build_parser().parse_args(['resume', '--task-id', 'd01-1', '--prompt', 'Update answer.txt'])
                with contextlib.redirect_stdout(buf):
                    assert d.cmd_resume(args) == 0
                resumed = json.loads(buf.getvalue())
                assert resumed['session_id'] == results[0]['session_id']
                assert (Path(results[0]['workdir']) / 'answer.txt').read_text(encoding='utf-8') == 'mock resume\n'
                results.append(resumed)
            state = json.loads(d.STATE_FILE.read_text(encoding='utf-8'))['tasks']
            assert len(state) == (2 if case['id'] in ('B04', 'B07') else 1)
            assert all(t['status'] == case['expected'] and not t['network'] for t in state.values())
            assert not (cwd / 'answer.txt').exists() and not (cwd / 'second.txt').exists()
            return sum((Path(x['run_dir']) / 'events.jsonl').stat().st_size for x in results)


def sample(case, harness, warm):
    start = time.perf_counter(); size = None; latency = None
    status = 'PASS'; detail = None
    try:
        with tempfile.TemporaryDirectory(prefix='alc-d01-') as tmp:
            home = Path(tmp); env = isolated_env(home)
            if case['id'] in ('B05', 'B06'):
                if harness:
                    fixture_db(home)
                    with contextlib.closing(sqlite3.connect(home / 'codex/state_5.sqlite')) as db:
                        assert db.execute('SELECT id FROM threads').fetchone() == ('fixture-thread-01',)
                else:
                    size, latency = mcp_probe(case, home, env, warm)
            elif harness:
                cwd = home / '中文 空格'; cwd.mkdir()
                rc, report, size = mock_run(case, cwd, env)
                assert report['status'] == case['expected'] and (rc == 0) == (case['expected'] == 'completed')
                if case['id'] == 'B03':
                    assert mock_run(case, cwd, env, True)[0] == 0
                if case['id'] == 'B04':
                    assert mock_run(case, cwd, env)[0] == 7
            else:
                size = dispatch_probe(case, home, env)
    except (FileNotFoundError, ImportError) as exc:
        status, detail = 'NOT_RUN', type(exc).__name__
    except Exception as exc:
        status, detail = 'FAIL', type(exc).__name__  # avoid leaking local paths/logs
    return dict(case=case['id'], status=status, detail=detail, latency_ms=round(latency if latency is not None else (time.perf_counter()-start)*1000, 3),
                payload_bytes=size, cache_state=('warm' if warm else 'cold') if not harness and case['id'] in ('B05','B06') else 'fresh',
                usage_source='unknown', input_tokens=None, output_tokens=None, real_model_calls=0)


def main():
    if not __debug__:
        raise SystemExit('assertions required; do not use python -O')
    ap = argparse.ArgumentParser(); ap.add_argument('--harness-only', action='store_true'); ap.add_argument('--repeat', type=int, default=5); ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if not 1 <= args.repeat <= 100:
        ap.error('repeat must be 1..100')
    rows = [sample(c,args.harness_only,w) for c in SUITE['cases'] for w in ([False,True] if not args.harness_only and c['id'] in ('B05','B06') else [False]) for _ in range(args.repeat)]
    groups = []
    for c in SUITE['cases']:
        for state in sorted({r['cache_state'] for r in rows if r['case']==c['id']}):
            group=[r for r in rows if r['case']==c['id'] and r['cache_state']==state]
            groups.append(dict(case=c['id'], cache_state=state, counts={s:sum(r['status']==s for r in group) for s in ('PASS','FAIL','NOT_RUN')}, latency=summarize([r['latency_ms'] for r in group if r['status']=='PASS'])))
    result=dict(schema_version=1, mode='harness-only' if args.harness_only else 'candidate-mock', upstream_commit=SUITE['upstream_commit'], baseline_commit=SUITE['baseline_commit'], checkout_commit=checkout_sha(), source_pins={**DISPATCH_FILES, **MCP_FILES}, reference_run=45915363640, environment=dict(os=platform.system(), python=platform.python_version(), node='not probed', codex='mock only', antigravity='NOT_RUN'), repeat=args.repeat, samples=rows, groups=groups)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(groups,indent=2))
    return 1 if any(r['status']!='PASS' for r in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
