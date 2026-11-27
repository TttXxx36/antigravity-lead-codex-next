import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const SERVER = path.join(ROOT, 'plugins', 'codex-console', 'server', 'index.mjs');

function createSyntheticCodexHome(codexHome, dispatchDir) {
  fs.mkdirSync(codexHome, { recursive: true });
  fs.mkdirSync(path.join(dispatchDir, 'runs', 'demo-task-1', 'turn-20261124-010000-abc123'), {
    recursive: true,
  });

  const nowSec = Math.floor(Date.now() / 1000);
  const nowMs = Date.now();

  // 1. state_5.sqlite
  const stateDb = new DatabaseSync(path.join(codexHome, 'state_5.sqlite'));
  stateDb.exec(`
    CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, metadata TEXT, position INTEGER, created_at_ms INTEGER, updated_at_ms INTEGER);
    CREATE TABLE project_roots (project_id TEXT, position INTEGER, path TEXT);
    CREATE TABLE thread_spawn_edges (parent_thread_id TEXT, child_thread_id TEXT PRIMARY KEY, status TEXT);
    CREATE TABLE threads (
      id TEXT PRIMARY KEY, rollout_path TEXT, created_at INTEGER, updated_at INTEGER,
      created_at_ms INTEGER, updated_at_ms INTEGER, source TEXT, thread_source TEXT,
      originator TEXT, cwd TEXT, title TEXT, name TEXT, preview TEXT,
      tokens_used INTEGER, archived INTEGER, is_pinned INTEGER, git_branch TEXT,
      git_sha TEXT, model TEXT, reasoning_effort TEXT, agent_nickname TEXT,
      agent_role TEXT, agent_path TEXT, project_id TEXT, history_mode TEXT
    );
  `);
  stateDb.prepare(`INSERT INTO projects VALUES ('proj-1', 'acme-api', '{}', 1, ?, ?)`).run(nowMs, nowMs);
  stateDb
    .prepare(
      `INSERT INTO threads VALUES (
        '01a90000-0000-7000-8000-000000000001', '', ?, ?, ?, ?, 'exec', 'user', 'codex_exec',
        '/tmp/worktrees/acme-api/demo-task-1', 'Implement JWT auth and unit tests', NULL,
        'Preview text', 1250000, 0, 0, 'agy-worker/demo-task-1', 'deadbeef', 'gpt-6.2-astra',
        'high', NULL, NULL, NULL, NULL, 'paginated'
      )`
    )
    .run(nowSec - 300, nowSec, nowMs - 300000, nowMs);
  stateDb
    .prepare(
      `INSERT INTO threads VALUES (
        '01a90000-0000-7000-8000-000000000002', '', ?, ?, ?, ?, 'vscode', 'user', 'codex_work_desktop',
        '/tmp/acme-api', 'Desktop chat thread', 'Desktop Refactor', 'Desktop preview',
        42000, 0, 0, 'main', 'cafebabe', 'gpt-6.2-sol', 'medium', NULL, NULL, NULL, 'proj-1', 'paginated'
      )`
    )
    .run(nowSec - 900, nowSec - 600, nowMs - 900000, nowMs - 600000);
  stateDb
    .prepare(
      `INSERT INTO threads VALUES (
        '01a90000-0000-7000-8000-000000000003', '', ?, ?, ?, ?, 'exec', 'user', 'codex_exec',
        '/tmp/worktrees/acme-api/demo-task-cleaned', 'Timed-out and cleaned task', NULL,
        'Cleaned preview', 512000, 0, 0, 'agy-worker/demo-task-cleaned', 'bead1234', 'gpt-6.2-astra',
        'xhigh', NULL, NULL, NULL, NULL, 'paginated'
      )`
    )
    .run(nowSec - 1200, nowSec - 600, nowMs - 1200000, nowMs - 600000);
  stateDb.close();

  // 2. goals_1.sqlite
  const goalsDb = new DatabaseSync(path.join(codexHome, 'goals_1.sqlite'));
  goalsDb.exec(`
    CREATE TABLE thread_goals (
      thread_id TEXT PRIMARY KEY, goal_id TEXT, objective TEXT, status TEXT,
      token_budget INTEGER, tokens_used INTEGER, time_used_seconds INTEGER,
      created_at_ms INTEGER, updated_at_ms INTEGER
    );
  `);
  goalsDb
    .prepare(
      `INSERT INTO thread_goals VALUES (
        '01a90000-0000-7000-8000-000000000002', 'goal-1', 'Refactor API router', 'blocked',
        2000000, 42000, 120, ?, ?
      )`
    )
    .run(nowMs - 900000, nowMs - 600000);
  goalsDb.close();

  // 3. queue_1.sqlite
  const queueDb = new DatabaseSync(path.join(codexHome, 'queue_1.sqlite'));
  queueDb.exec(`
    CREATE TABLE queued_items (
      id TEXT PRIMARY KEY, thread_id TEXT, payload_json TEXT, queue_order INTEGER,
      created_at_ms INTEGER, updated_at_ms INTEGER
    );
  `);
  queueDb.close();

  // 4. thread_history_1.sqlite
  const histDb = new DatabaseSync(path.join(codexHome, 'thread_history_1.sqlite'));
  histDb.exec(`
    CREATE TABLE thread_turns (
      thread_id TEXT, turn_id TEXT, rollout_ordinal INTEGER, status TEXT,
      error_json TEXT, started_at INTEGER, completed_at INTEGER, duration_ms INTEGER
    );
    CREATE TABLE thread_items (
      thread_id TEXT, turn_id TEXT, item_id TEXT, rollout_ordinal INTEGER,
      created_at_ms INTEGER, item_type TEXT, item_json TEXT
    );
  `);
  histDb
    .prepare(
      `INSERT INTO thread_turns VALUES (
        '01a90000-0000-7000-8000-000000000001', 'turn-1', 1, 'inProgress', NULL, ?, NULL, NULL
      )`
    )
    .run(nowSec - 60);
  histDb
    .prepare(
      `INSERT INTO thread_turns VALUES (
        '01a90000-0000-7000-8000-000000000003', 'turn-1', 1, 'inProgress', NULL, ?, NULL, NULL
      )`
    )
    .run(nowSec - 1200);
  histDb
    .prepare(
      `INSERT INTO thread_items VALUES (
        '01a90000-0000-7000-8000-000000000001', 'turn-1', 'item-1', 1, ?, 'userMessage', ?
      )`
    )
    .run(nowMs - 55000, JSON.stringify({ content: [{ type: 'text', text: 'Build JWT auth' }] }));
  histDb
    .prepare(
      `INSERT INTO thread_items VALUES (
        '01a90000-0000-7000-8000-000000000001', 'turn-1', 'item-2', 2, ?, 'agentMessage', ?
      )`
    )
    .run(
      nowMs - 5000,
      JSON.stringify({
        text: JSON.stringify({ status: 'completed', summary: 'Implemented JWT auth with 18 passing tests.' }),
      })
    );
  histDb.close();

  // 5. Synthetic rollout JSONL with dual 5h (49% used -> 51% rem) + weekly (12% used -> 88% rem)
  const sessionsDir = path.join(codexHome, 'sessions', '2026', '11', '24');
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.writeFileSync(
    path.join(sessionsDir, 'rollout-2026-11-24T17-00-00-01a90000.jsonl'),
    JSON.stringify({
      timestamp: new Date(nowMs).toISOString(),
      type: 'event_msg',
      payload: {
        type: 'token_count',
        rate_limits: {
          limit_id: 'codex',
          plan_type: 'plus',
          primary: { used_percent: 49.0, window_minutes: 300, resets_at: nowSec + 7200 },
          secondary: { used_percent: 12.0, window_minutes: 10080, resets_at: nowSec + 259200 },
          credits: { has_credits: false, unlimited: false, balance: '0' },
        },
      },
    }) + '\n'
  );

  // 6. multi-agent-dispatch state.json + nested turn result.json
  fs.writeFileSync(
    path.join(dispatchDir, 'state.json'),
    JSON.stringify({
      rr_counter: 1,
      tasks: {
        'demo-task-1': {
          task_id: 'demo-task-1',
          backend: 'codex',
          model: 'gpt-6.2-astra',
          effort: 'high',
          difficulty: 'hard',
          repo_root: '/tmp/acme-api',
          worktree_path: '/tmp/worktrees/acme-api/demo-task-1',
          branch: 'agy-worker/demo-task-1',
          isolation: 'worktree',
          sandbox: 'workspace-write',
          session_id: '01a90000-0000-7000-8000-000000000001',
          status: 'running',
          exit_code: null,
          created_at: '2026-11-24T00:00:00+00:00',
          updated_at: '2026-11-24T01:00:00+00:00',
          run_dir: path.join(dispatchDir, 'runs', 'demo-task-1'),
        },
        'demo-task-cleaned': {
          task_id: 'demo-task-cleaned',
          backend: 'codex',
          model: 'gpt-6.2-astra',
          effort: 'xhigh',
          difficulty: 'hard',
          repo_root: '/tmp/acme-api',
          worktree_path: '/tmp/worktrees/acme-api/demo-task-cleaned',
          branch: 'agy-worker/demo-task-cleaned',
          isolation: 'worktree',
          sandbox: 'workspace-write',
          session_id: '01a90000-0000-7000-8000-000000000003',
          status: 'cleaned',
          exit_code: 124,
          created_at: '2026-11-24T00:00:00+00:00',
          updated_at: '2026-11-24T00:15:00+00:00',
          run_dir: path.join(dispatchDir, 'runs', 'demo-task-cleaned'),
        },
      },
    })
  );
  fs.writeFileSync(
    path.join(dispatchDir, 'runs', 'demo-task-1', 'turn-20261124-010000-abc123', 'result.json'),
    JSON.stringify({
      report: {
        status: 'completed',
        summary: 'Resume turn verified all 18 tests cleanly.',
        files_modified: ['src/auth.py', 'tests/test_auth.py'],
        verification_passed: true,
        risks_or_followups: [],
      },
    })
  );
}

async function runTests() {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'alc-test-'));
  const codexHome = path.join(tmpRoot, 'codex-home');
  const dispatchDir = path.join(tmpRoot, 'dispatch-state');
  const pluginData = path.join(tmpRoot, 'plugin-data');

  let child;
  let closed;
  try {
    createSyntheticCodexHome(codexHome, dispatchDir);
    const globalConfig=path.join(tmpRoot,'empty-gitconfig');
    fs.writeFileSync(globalConfig,'');
    const allowed = ['PATH', 'Path', 'SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP'];
    const env = Object.fromEntries(allowed.filter(k => process.env[k] !== undefined).map(k => [k, process.env[k]]));
    // Use a native Node executable, not Bash, on all platforms. Quota probes
    // target Node in the empty synthetic directory, never a real Codex CLI.
    child = spawn(process.execPath, ['--no-warnings', SERVER, '--data-dir', pluginData], {
      cwd: tmpRoot,
      env: {
        ...env, HOME: tmpRoot, USERPROFILE: tmpRoot,
        CODEX_BIN: process.execPath,
        CODEX_HOME: codexHome,
        AGY_DISPATCH_STATE_DIR: dispatchDir,
        GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: globalConfig, GIT_TERMINAL_PROMPT: '0',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    closed = new Promise(resolve => child.once('close', resolve));
    child.on('error', () => {});
    child.stdout.setEncoding('utf8');

    let buf = '';
    const pending = new Map();
    let nextId = 1;
    let stderr = '';
    child.stderr.on('data', (d) => {
      stderr += d.toString('utf8');
    });
    child.stdout.on('data', (chunk) => {
      buf += chunk.toString('utf8');
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (!line) continue;
        const msg = JSON.parse(line);
        if (msg.id && pending.has(msg.id)) {
          pending.get(msg.id)(msg);
          pending.delete(msg.id);
        }
      }
    });

    const rpc = (method, params = {}) =>
      new Promise((resolve, reject) => {
        const id = nextId++;
        const timer = setTimeout(() => reject(new Error(`RPC timeout: ${method} (stderr: ${stderr})`)), 10000);
        pending.set(id, (msg) => {
          clearTimeout(timer);
          resolve(msg);
        });
        child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
      });

    // 1. Initialize
    const init = await rpc('initialize', {
      protocolVersion: '2025-03-26',
      capabilities: {},
      clientInfo: { name: 'ci-test', version: '1.0.0' },
    });
    assert.ok(init.result?.capabilities?.tools, 'tools capability advertised');
    assert.ok(init.result?.capabilities?.resources, 'resources capability advertised');
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');

    // 2. Verify tools & UI entrypoints metadata
    const toolsRes = await rpc('tools/list');
    const openTool = toolsRes.result.tools.find((t) => t.name === 'open_codex_console');
    assert.equal(openTool?._meta?.ui?.resourceUri, 'ui://codex-console/app.html');
    assert.equal(openTool?._meta?.['com.google.antigravity/ui']?.entrypoints?.length, 2);

    // 3. Verify bundled single-file HTML resource
    const resRead = await rpc('resources/read', { uri: 'ui://codex-console/app.html' });
    assert.equal(resRead.result.contents[0].mimeType, 'text/html;profile=mcp-app');
    assert.ok(resRead.result.contents[0].text.length > 10000, 'bundled app.html is non-empty');

    // 4. Verify console_snapshot merges Codex DBs + dispatch turn result & unwraps JSON reply
    const snapRes = await rpc('tools/call', { name: 'console_snapshot', arguments: { limit: 50 } });
    const snap = snapRes.result.structuredContent;
    assert.equal(snap.connected, true);
    assert.equal(snap.stats.runningCount, 1);
    assert.equal(snap.stats.goalBlockedCount, 1);
    assert.equal(snap.stats.agyCount, 2);
    assert.equal(snap.stats.managedCount, 2);
    const agyTask = snap.tasks.find((t) => t.id === '01a90000-0000-7000-8000-000000000001');
    const cleanedTask = snap.tasks.find((t) => t.id === '01a90000-0000-7000-8000-000000000003');
    assert.equal(cleanedTask.status.code, 'exec_done');
    assert.equal(cleanedTask.status.label, '已清理(曾超时)');
    const cleanedAgent = snap.managedAgents.find((m) => m.id === 'demo-task-cleaned');
    assert.equal(cleanedAgent.status, 'cleaned');
    assert.equal(agyTask.isManagedDispatch, true);
    assert.equal(agyTask.latestReply, 'Implemented JWT auth with 18 passing tests.');
    const demoAgent = snap.managedAgents.find((m) => m.id === 'demo-task-1');
    assert.equal(demoAgent.summary, 'Resume turn verified all 18 tests cleanly.');
    assert.equal(demoAgent.changedFiles.length, 2);

    // 4b. Verify dual-window quota picks minimum remaining (5h 51% < weekly 88%)
    assert.equal(snap.quota?.available, true);
    assert.equal(snap.quota?.planType, 'plus');
    assert.equal(snap.quota?.windows?.length, 2);
    assert.equal(snap.quota?.bottleneck?.key, '5h');
    assert.equal(snap.quota?.bottleneck?.remainingPercent, 51);

    // 5. Verify local pin, custom title & soft-hide drawer persistence
    await rpc('tools/call', {
      name: 'console_toggle_pin',
      arguments: { threadId: agyTask.id, pinned: true, customTitle: 'Auth Service Worker' },
    });
    const snap2 = (await rpc('tools/call', { name: 'console_snapshot', arguments: {} })).result.structuredContent;
    const pinnedTask = snap2.tasks.find((t) => t.id === agyTask.id);
    assert.equal(pinnedTask.pinned, true);
    assert.equal(pinnedTask.hidden, false);
    assert.equal(pinnedTask.title, 'Auth Service Worker');

    await rpc('tools/call', {
      name: 'console_toggle_pin',
      arguments: { threadId: agyTask.id, hidden: true },
    });
    const snapHidden = (await rpc('tools/call', { name: 'console_snapshot', arguments: {} })).result.structuredContent;
    const hiddenTask = snapHidden.tasks.find((t) => t.id === agyTask.id);
    assert.equal(hiddenTask.hidden, true);
    assert.equal(hiddenTask.pinned, false);

    await rpc('tools/call', {
      name: 'console_toggle_pin',
      arguments: { threadId: agyTask.id, hidden: false },
    });

    // 6. Verify cross-session collaboration bindings CRUD
    const upsertRes = await rpc('tools/call', {
      name: 'manage_collab_binding',
      arguments: {
        action: 'upsert',
        changeKey: 'change-jwt-auth',
        goalTitle: 'Implement JWT Auth',
        threadId: agyTask.id,
        ownerRole: 'codex',
        status: 'active',
      },
    });
    const bindingId = upsertRes.result.structuredContent.binding.id;
    assert.ok(bindingId);
    const listBindings = (await rpc('tools/call', { name: 'manage_collab_binding', arguments: { action: 'list' } }))
      .result.structuredContent.bindings;
    assert.equal(listBindings.length, 1);
    await rpc('tools/call', { name: 'manage_collab_binding', arguments: { action: 'delete', id: bindingId } });

    // Add 300 older sessions after original fixture assertions.
    const oldDb = new DatabaseSync(path.join(codexHome,'state_5.sqlite'));
    const insert = oldDb.prepare("INSERT INTO threads(id,created_at,updated_at,source,thread_source,originator,cwd,title,preview,archived,is_pinned) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
    const now=Math.floor(Date.now()/1000);
    oldDb.exec('BEGIN');
    for(let i=0;i<300;i++) insert.run('historical-'+String(i).padStart(4,'0'),now-10000-i,now-10000-i,'vscode','user','codex_work_desktop',tmpRoot,'History '+i,'old',0,0);
    oldDb.exec('COMMIT');oldDb.close();
    const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    const codexFiles=['state_5.sqlite','goals_1.sqlite','queue_1.sqlite','thread_history_1.sqlite'].map(x=>path.join(codexHome,x));
    const before=codexFiles.map(sha);
    const detailName='get_codex_task_detail';
    for (const id of ['historical-0200','historical-0249','historical-0299']) {
      const reply=await rpc('tools/call',{name:detailName,arguments:{threadId:id}});
      assert.equal(reply.result?.structuredContent?.task?.id,id,JSON.stringify(reply));
    }
    const ambiguous=await rpc('tools/call',{name:detailName,arguments:{threadId:'historical-0'}});
    assert.equal(ambiguous.result?.isError,true);
    assert.match(ambiguous.result?.structuredContent?.error||'',/Ambiguous/);
    const literal=await rpc('tools/call',{name:detailName,arguments:{threadId:'historical-%'}});
    assert.equal(literal.result?.isError,true);
    assert.deepEqual(codexFiles.map(sha),before,'read-only Codex DB bytes changed');
    // Denied before spawn: no trusted host grant or unmanaged queue.
    for (const args of [
      {name:'spawn_codex_worker',arguments:{cwd:tmpRoot,prompt:'synthetic',network:true}},
      {name:'send_codex_message',arguments:{threadId:agyTask.id,message:'synthetic',mode:'queue'}},
      {name:'send_codex_message',arguments:{threadId:agyTask.id,message:'synthetic',mode:'resume'}},
    ]) {
      const denied=await rpc('tools/call',args);
      assert.equal(denied.result?.isError,true, JSON.stringify(denied.result));
    }
    const incompatible=new DatabaseSync(path.join(codexHome,'state_5.sqlite'));
    incompatible.exec('ALTER TABLE threads RENAME TO incompatible_threads');
    incompatible.close();
    const broken=await rpc('tools/call',{name:'console_snapshot',arguments:{limit:50}});
    assert.equal(broken.result?.structuredContent?.connected,false);
    assert.ok(broken.result?.structuredContent?.health?.errors?.some(e=>e.source==='state_5.sqlite'&&e.code!=='MISSING'));
    const unavailable=await rpc('tools/call',{name:detailName,arguments:{threadId:'historical-0299'}});
    assert.equal(unavailable.result?.isError,true);
    assert.match(unavailable.result?.structuredContent?.error||'',/State database unavailable/);
    console.log('[PASS] All MCP Codex Console integration tests passed, including >250 historical tasks, ambiguity, read-only hashes and schema errors.');
  } finally {
    if (child) {
      child.kill();
      let timer;
      try {
        await Promise.race([closed, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('MCP shutdown timeout')), 5000); })]);
      } finally { clearTimeout(timer); }
    }
    fs.rmSync(tmpRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
}

runTests().catch((err) => {
  console.error('[FAIL]', err);
  process.exit(1);
});
