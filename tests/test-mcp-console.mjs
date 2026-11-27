import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
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

    for (const name of ['task_status','task_result','task_delta','get_operation_status','task_logs','task_list']) {
      assert.deepEqual(toolsRes.result.tools.find(t=>t.name===name)?._meta?.ui?.visibility,['model']);
    }
    for (const name of ['get_codex_task_detail','list_codex_tasks','console_get_op']) {
      assert.deepEqual(toolsRes.result.tools.find(t=>t.name===name)?._meta?.ui?.visibility,['app']);
    }
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

    const compactCall=async(name,args,budget=1500)=>{
      const reply=(await rpc('tools/call',{name,arguments:args})).result;
      assert.ok(reply && !reply.isError,JSON.stringify(reply));
      assert.equal(reply.structuredContent,undefined);
      assert.equal(reply.content.length,1);
      assert.ok(Buffer.byteLength(reply.content[0].text,'utf8')<=budget);
      return JSON.parse(reply.content[0].text);
    };
    const small=await compactCall('task_status',{threadId:agyTask.id},600);
    assert.equal(small.status,'running');
    assert.equal(small.verification,'unknown');
    assert.equal(small.summary,undefined);
    const result=await compactCall('task_result',{threadId:agyTask.id});
    assert.equal(result.summary,'Implemented JWT auth with 18 passing tests.');
    const managed=await compactCall('task_status',{taskId:'demo-task-1'},600);
    assert.equal(managed.status,'running');
    const current=await compactCall('task_delta',{threadId:agyTask.id});
    assert.equal(current.changed,true);
    const unchanged=await compactCall('task_delta',{threadId:agyTask.id,revision:current.revision});
    assert.equal(unchanged.changed,false);
    assert.equal(unchanged.result,undefined);
    const page=await compactCall('task_logs',{threadId:agyTask.id,limit:1});
    assert.equal(page.entries.length,1);
    assert.equal(page.hasMore,true);
    assert.equal(page.entries[0].text,undefined);
    const page2=await compactCall('task_logs',{threadId:agyTask.id,cursor:page.nextCursor,limit:1});
    assert.equal(page2.entries.length,1);
    assert.ok(page2.nextCursor>page.nextCursor);
    assert.equal(page2.hasMore,false);
    const absent=(await rpc('tools/call',{name:'get_operation_status',arguments:{opId:'not-found'}})).result;
    assert.equal(absent.isError,true);
    assert.equal(absent.structuredContent,undefined);
    // Positive operation lookup; no prompt/output is serialized.
    const fixtureOps=new DatabaseSync(path.join(pluginData,'console.sqlite'));
    fixtureOps.prepare("INSERT INTO console_ops(id,thread_id,op_type,prompt,status,output_text,started_at,duration_ms) VALUES(?,?,?,?,?,?,?,?)").run('op-fixture',agyTask.id,'mock','PRIVATE_PROMPT','succeeded','PRIVATE_OUTPUT',1,7);
    fixtureOps.close();
    const op=await compactCall('get_operation_status',{opId:'op-fixture'},600);
    assert.deepEqual(op,{opId:'op-fixture',threadId:agyTask.id,status:'succeeded',durationMs:7});
    // State-published terminal artifact with exact identity and digest.
    const stateFile=path.join(dispatchDir,'state.json');
    const originalState=fs.readFileSync(stateFile,'utf8');
    const fixtureState=JSON.parse(originalState);
    const fixtureId='boundary-test';
    const fixtureRun=path.join(dispatchDir,'runs',fixtureId);
    const artifact=path.join(fixtureRun,'result.json');
    fs.mkdirSync(fixtureRun,{recursive:true});
    const value={task_id:fixtureId,session_id:'session-fixture',exit_code:0,task_status:'completed',report:{status:'completed',summary:'current fixture',verification_passed:true}};
    const record={task_id:fixtureId,run_dir:fixtureRun,session_id:value.session_id,exit_code:0,task_status:'completed',status:'completed'};
    fixtureState.tasks[fixtureId]=record;
    const publish=bytes=>{
      fs.writeFileSync(artifact,bytes);
      record.result_ref={turn:null,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
      fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    };
    const readFixture=()=>compactCall('task_result',{taskId:fixtureId});
    publish(JSON.stringify(value));
    let found=await readFixture();
    assert.equal(found.reportAvailable,true);assert.equal(found.summary,'current fixture');assert.equal(found.verification,'unknown');

    // D14: reconnect with explicit turn/seq; gaps and malformed ordering fail safely.
    record.stream_events=true;record.status='running';
    fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    const streamFile=path.join(fixtureRun,'stream-state.json');
    const streamEntries=[{seq:5,kind:'running',at:1,stdoutBytes:0,stderrBytes:0,lines:0},
      {seq:6,kind:'progress',at:2,stdoutBytes:10,stderrBytes:2,lines:1,private:'NO_RAW_OUTPUT'}];
    const streamSnapshot={version:1,taskId:fixtureId,turnId:'initial',entries:streamEntries};
    fs.writeFileSync(streamFile,JSON.stringify(streamSnapshot));
    const replay=await compactCall('task_events',{taskId:fixtureId,limit:1},2500);
    assert.equal(replay.gap,true);assert.equal(replay.nextCursor,5);assert.equal(replay.hasMore,true);
    const reconnect=await compactCall('task_events',{taskId:fixtureId,turnId:replay.turnId,cursor:replay.nextCursor},2500);
    assert.equal(reconnect.gap,false);assert.equal(reconnect.nextCursor,6);assert.equal(reconnect.entries[0].private,undefined);
    assert.equal(reconnect.verification,'unknown');
    const taskEntries=streamEntries.map(e=>({...e,taskSeq:e.seq}));
    const taskSnapshot={...streamSnapshot,version:2,sequenceBase:0,sequenceScope:'task',entries:taskEntries};
    fs.writeFileSync(streamFile,JSON.stringify(taskSnapshot));
    const taskReplay=await compactCall('task_events',{taskId:fixtureId,limit:2},2500);
    assert.equal(taskReplay.sequenceScope,'task');assert.equal(taskReplay.entries[1].taskSeq,6);
    fs.writeFileSync(streamFile,JSON.stringify({...taskSnapshot,entries:[taskEntries[0],{...taskEntries[1],taskSeq:8}]}));
    const badTaskSequence=(await rpc('tools/call',{name:'task_events',arguments:{taskId:fixtureId}})).result;
    assert.equal(badTaskSequence.isError,true);
    fs.writeFileSync(streamFile,JSON.stringify({...streamSnapshot,entries:[streamEntries[0],{...streamEntries[1],seq:8}]}));
    const invalidStream=(await rpc('tools/call',{name:'task_events',arguments:{taskId:fixtureId}})).result;
    assert.equal(invalidStream.isError,true);
    fs.unlinkSync(streamFile);delete record.stream_events;
    record.status='completed';fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    record.status='running';fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    assert.equal((await readFixture()).reportAvailable,false);
    record.status='completed';fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    fs.writeFileSync(artifact,JSON.stringify({...value,report:{...value.report,summary:'stale changed'}}));
    assert.equal((await readFixture()).reportAvailable,false);
    publish(JSON.stringify({...value,task_id:'different'}));
    assert.equal((await readFixture()).reportAvailable,false);
    publish(JSON.stringify({...value,report:{...value.report,summary:'x'.repeat(263000)}}));
    assert.equal((await readFixture()).reportAvailable,false);
    publish(JSON.stringify(value));
    record.result_ref.turn='turn-missing';fs.writeFileSync(stateFile,JSON.stringify(fixtureState));
    assert.equal((await readFixture()).reportAvailable,false);
    publish(JSON.stringify(value));
    fs.unlinkSync(artifact);
    const outside=path.join(tmpRoot,'outside-result.json');
    fs.writeFileSync(outside,JSON.stringify(value));
    let linked=false;
    try { fs.symlinkSync(outside,artifact,'file');linked=true; } catch(err) { console.log('[SKIP] file symlink unavailable: '+err.code); }
    if(linked){assert.equal((await readFixture()).reportAvailable,false);fs.unlinkSync(artifact);}
    // Directory junction on Windows exercises the escape even if file links are unavailable.
    const redirect=path.join(tmpRoot,'outside-run');fs.mkdirSync(redirect);
    fs.writeFileSync(path.join(redirect,'result.json'),JSON.stringify(value));
    fs.rmSync(fixtureRun,{recursive:true,force:true});
    fs.symlinkSync(redirect,fixtureRun,process.platform==='win32'?'junction':'dir');
    assert.equal((await readFixture()).reportAvailable,false);
    fs.unlinkSync(fixtureRun);

    // D15 cross-language test: real Python migration, read-only native MCP,
    // transactional corruption rejection and inverse migration on isolated fixture.
    const quiet=JSON.parse(originalState);
    for(const task of Object.values(quiet.tasks)){
      if(['running','reserved','interrupted'].includes(task.status))task.status='completed';
      delete task.active_turn_id;
    }
    fs.writeFileSync(stateFile,JSON.stringify(quiet));
    const python=process.platform==='win32'?'python':'python3';
    const dispatchScript=path.join(ROOT,'skills','multi-agent-dispatch','scripts','dispatch.py');
    const nativeState=path.join(codexHome,'state_5.sqlite');
    const nativeBefore=crypto.createHash('sha256').update(fs.readFileSync(nativeState)).digest('hex');
    const storageCmd=(...args)=>JSON.parse(execFileSync(python,[dispatchScript,...args],{
      env:{...env,CODEX_HOME:codexHome,AGY_DISPATCH_STATE_DIR:dispatchDir,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'},
      encoding:'utf8',timeout:20000
    }));
    const migrated=storageCmd('state-migrate','--confirm-quiescent');
    assert.equal(migrated.status,'migrated');
    assert.equal((await compactCall('task_status',{taskId:'demo-task-1'},600)).status,'completed');
    const marker=JSON.parse(fs.readFileSync(stateFile,'utf8'));
    const owned=path.join(dispatchDir,marker.database);
    const checkDb=new DatabaseSync(owned);
    try {
      const row=checkDb.prepare('SELECT payload_sha256 FROM dispatch_tasks WHERE task_id=?').get('demo-task-1');
      checkDb.prepare('UPDATE dispatch_tasks SET payload_sha256=? WHERE task_id=?').run('0'.repeat(64),'demo-task-1');
      assert.equal((await rpc('tools/call',{name:'task_status',arguments:{taskId:'demo-task-1'}})).result.isError,true);
      checkDb.prepare('UPDATE dispatch_tasks SET payload_sha256=? WHERE task_id=?').run(row.payload_sha256,'demo-task-1');
    }finally{checkDb.close();}
    assert.equal(storageCmd('state-rollback','--confirm-quiescent').status,'rolled_back');
    assert.equal((await compactCall('task_status',{taskId:'demo-task-1'},600)).status,'completed');
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(nativeState)).digest('hex'),nativeBefore);
    fs.writeFileSync(stateFile,originalState);
    console.log('[PASS] D15 actual Python migration / MCP read / corrupt manifest rejection / inverse migration / native DB hash preserved');
    console.log('[PASS] D09 positive op, current digest-bound artifact, running/stale/missing/oversized/identity/link rejection');
    const traversal=(await rpc('tools/call',{name:'task_result',arguments:{taskId:'../secret'}})).result;
    assert.equal(traversal.isError,true);
    const both=(await rpc('tools/call',{name:'task_status',arguments:{threadId:agyTask.id,taskId:'demo-task-1'}})).result;
    assert.equal(both.isError,true);
    const listing=await compactCall('task_list',{limit:2},4000);
    assert.equal(listing.tasks.length,2);
    assert.equal(listing.tasks[0].title,undefined);
    const legacy=(await rpc('tools/call',{name:'get_codex_task_detail',arguments:{threadId:agyTask.id}})).result;
    assert.ok(legacy.structuredContent.messages.length>0);
    assert.ok(Buffer.byteLength(JSON.stringify(legacy))>Buffer.byteLength(JSON.stringify(small)));
    console.log('[PASS] D09 compact MCP text-only response, bounded payload, delta, cursor, legacy UI metadata and invalid selectors');

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
