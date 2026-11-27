"""CI-only orchestration of fixed D01 Mock baseline. No real model or private data."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from run_benchmark import ROOT, isolated_env, verify_sources, DISPATCH_FILES, MCP_FILES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeat', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not __debug__ or not 1 <= args.repeat <= 20:
        parser.error('assertions required; repeat must be 1..20')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='d01-ci-') as tmp:
        home = Path(tmp)
        env = isolated_env(home)
        env['CODEX_BIN'] = sys.executable  # explicit non-Codex binary; quota app-server probe fails closed
        env['PYTHON_BIN'] = sys.executable
        env['CODEX_CONSOLE_NODE_BIN'] = shutil.which('node') or ''
        env['TMPDIR'] = str(home)
        env['TEMP'] = str(home)
        env['TMP'] = str(home)
        # Only read version metadata, never run a real Codex binary.
        def command(cmd, timeout=20):
            try:
                p = subprocess.run(cmd, cwd=ROOT, env=env, text=True, encoding='utf-8',
                                   errors='replace', capture_output=True, timeout=timeout)
                return p.returncode, p.stdout.strip()[:200]
            except (OSError, subprocess.TimeoutExpired):
                return None, None

        versions = {name: command(cmd)[1] for name, cmd in {
            'checkout_commit': ['git','rev-parse','HEAD'], 'python': [sys.executable,'--version'],
            'node': ['node','--version'], 'git': ['git','--version']}.items()}
        versions.update(os=platform.system(), release=platform.release(),
                        codex='MOCK_ONLY', antigravity='NOT_RUN', model_usage='unknown')
        def execute(name, cmd, *, timeout=240, skip=None):
            row = dict(name=name, status='NOT_RUN', exit_code=None, detail=skip)
            start = time.monotonic()
            if skip is None:
                try:
                    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=timeout,
                                       text=True, encoding='utf-8', errors='replace')
                    row.update(status='PASS' if p.returncode == 0 else 'FAIL', exit_code=p.returncode)
                    # Only synthetic outputs; raw diagnostics are not archived.
                    if p.returncode:
                        row['detail'] = 'nonzero exit; inspect structured result when available'
                        # Only synthetic fixtures, versioned source, and isolated env are used here.
                        # Emit the tail of diagnostics to Actions, not to persistent artifacts.
                        print((p.stderr or p.stdout)[-6000:], flush=True)
                    print(name, row['status'], p.returncode, flush=True)
                except subprocess.TimeoutExpired:
                    row.update(status='FAIL', detail='timeout')
                except OSError as exc:
                    row.update(detail=type(exc).__name__)
            row['elapsed_ms'] = round((time.monotonic()-start)*1000, 3)
            records.append(row)
        try:
            verify_sources({**DISPATCH_FILES, **MCP_FILES})
            records.append(dict(name='candidate-source-hashes',status='PASS',exit_code=0))
        except (OSError, ValueError) as exc:
            records.append(dict(name='candidate-source-hashes',status='FAIL',exit_code=None,detail=type(exc).__name__))
            (out/'summary.json').write_text(json.dumps(dict(environment=versions, tests=records),indent=2),encoding='utf-8')
            return 1
        py = sys.executable
        execute('harness', [py,'benchmarks/run_benchmark.py','--harness-only','--repeat',str(args.repeat),'--output',str(out/'harness.json')])
        execute('full-dispatch-contract', [py,'benchmarks/dispatch_contract.py','--repeat',str(args.repeat),'--output',str(out/'dispatch-contract.json')])
        execute('candidate-mock', [py,'benchmarks/run_benchmark.py','--repeat',str(args.repeat),'--output',str(out/'baseline.json')], timeout=480)
        execute('original-python-tests',[py,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'])
        # Native Node integration runs on all platforms, including Windows.
        missing = not (ROOT/'plugins/codex-console/node_modules/@modelcontextprotocol/sdk').is_dir()
        execute('native-mcp-integration',['node','--no-warnings','tests/test-mcp-console.mjs'],timeout=120,skip='runtime dependencies missing' if missing else None)
    result = dict(environment=versions, repeat=args.repeat, tests=records, real_model_calls=0,
                  reference_run=45915363640, mode='windows-repair-candidate', note='Non-PASS is an unresolved candidate result; original baseline is preserved.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 1 if any(r['status']!='PASS' for r in records) else 0


if __name__ == '__main__':
    raise SystemExit(main())
