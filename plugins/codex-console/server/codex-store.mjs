import { DatabaseSync } from 'node:sqlite';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { runtimePaths } from './platform.mjs';

const { codexHome: CODEX_HOME, dispatchStateDir: DISPATCH_STATE_DIR } = runtimePaths();

function withReadOnlyDb(dbFile, fn, fallback, errors = []) {
  if (!fs.existsSync(dbFile)) { errors.push({source:path.basename(dbFile),code:'MISSING'}); return fallback; }
  let db = null;
  try {
    db = new DatabaseSync(dbFile, { readOnly: true });
    db.exec('PRAGMA busy_timeout = 2000;');
    return fn(db);
  } catch (err) {
    errors.push({source:path.basename(dbFile),code:err?.code || 'READ_ERROR',message:'SQLite read/schema incompatible'});
    return fallback;
  } finally {
    if (db) {
      try {
        db.close();
      } catch {
        // ignore
      }
    }
  }
}

function readDispatchState(errors = []) {
  const statePath = path.join(DISPATCH_STATE_DIR, 'state.json');
  if (!fs.existsSync(statePath)) return { tasks: {} };
  try {
    const raw = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    if (!raw || typeof raw !== 'object' || !raw.tasks || Array.isArray(raw.tasks) || typeof raw.tasks !== 'object') throw new Error('Invalid state');
    return raw;
  } catch {
    errors.push({source:'state.json',code:'INVALID_STATE',message:'Dispatcher state unreadable; not reset'});
    return { tasks: {} };
  }
}

function readDispatchRunResult(runDir) {
  if (!runDir || !fs.existsSync(runDir)) return null;
  // Prefer the newest resume turn's result.json over the initial run's result.json
  const candidates = [];
  try {
    const entries = fs.readdirSync(runDir, { withFileTypes: true });
    const turnDirs = entries
      .filter((e) => e.isDirectory() && e.name.startsWith('turn-'))
      .map((e) => path.join(runDir, e.name, 'result.json'))
      .filter((p) => fs.existsSync(p))
      .sort()
      .reverse();
    candidates.push(...turnDirs);
  } catch {
    // ignore
  }
  const rootResult = path.join(runDir, 'result.json');
  if (fs.existsSync(rootResult)) candidates.push(rootResult);

  for (const p of candidates) {
    try {
      const parsed = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (parsed && typeof parsed === 'object') return parsed;
    } catch {
      // try next candidate
    }
  }
  return null;
}

function unwrapStructuredReply(rawText) {
  const trimmed = (rawText || '').trim();
  if (!trimmed) return '';
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const obj = JSON.parse(trimmed);
      if (obj && typeof obj.summary === 'string' && obj.summary.trim()) {
        return obj.summary.trim();
      }
    } catch {
      // fall through
    }
  }
  return trimmed;
}

function parseWorktreeLabel(cwd) {
  if (!cwd) return null;
  cwd = cwd.replaceAll('\\', '/');
  // Pattern 1: ~/.local/state/multi-agent-dispatch/worktrees/<repo>/<task>
  let m = cwd.match(/\/worktrees\/([^/]+)\/([^/]+)$/);
  if (m) return `${m[1]}/${m[2]}`;
  // Pattern 2: ~/.codex/worktrees/<wt>/<repo>
  m = cwd.match(/\.codex\/worktrees\/([^/]+)/);
  if (m) return m[1];
  // Pattern 3: generic /worktrees/<name>
  m = cwd.match(/\/worktrees\/([^/]+)/);
  if (m) return m[1];
  return null;
}

function parseSubagentMeta(row) {
  const isSub =
    row.thread_source === 'subagent' ||
    (typeof row.source === 'string' && row.source.startsWith('{"subagent"'));
  if (!isSub) return { isSubagent: false, parentThreadId: null, agentPath: row.agent_path || null };
  let parentThreadId = null;
  let agentPath = row.agent_path || null;
  let nickname = row.agent_nickname || null;
  try {
    if (typeof row.source === 'string' && row.source.startsWith('{')) {
      const parsed = JSON.parse(row.source);
      const spawn = parsed?.subagent?.thread_spawn;
      if (spawn) {
        parentThreadId = spawn.parent_thread_id || null;
        agentPath = spawn.agent_path || agentPath;
        nickname = spawn.agent_nickname || nickname;
      }
    }
  } catch {
    // ignore
  }
  return { isSubagent: true, parentThreadId, agentPath, nickname };
}

function cleanDisplayTitle({ customTitle, threadName, dispatchTask, rawTitle, preview, agentNickname, agentPath, id }) {
  if (customTitle && customTitle.trim()) return customTitle.trim();
  if (threadName && threadName.trim()) return threadName.trim();
  if (dispatchTask?.task_id) {
    const repo = dispatchTask.repo_root ? path.basename(dispatchTask.repo_root) : '';
    return repo ? `${repo} · ${dispatchTask.task_id}` : dispatchTask.task_id;
  }
  if (agentNickname || agentPath) {
    const roleTag = agentPath ? agentPath.replace(/^\/root\//, '') : '';
    if (agentNickname && roleTag) return `${agentNickname} (${roleTag})`;
  }
  const candidate = (rawTitle || preview || '').replace(/\s+/g, ' ').trim();
  if (!candidate) return `Thread ${id.slice(0, 8)}`;
  const stripped = candidate
    .replace(/^Read\s+docs\/BLACKBOARD\.md\s+thoroughly\s+first\s*(and|\.)?\s*/i, '')
    .trim();
  const base = stripped || candidate;
  return base.length > 72 ? `${base.slice(0, 70)}…` : base;
}

function deriveProjectName(row, projectsById, projectRoots, dispatchTask) {
  if (row.project_id && projectsById.has(row.project_id)) {
    return projectsById.get(row.project_id);
  }
  if (dispatchTask?.repo_root) {
    return path.basename(dispatchTask.repo_root);
  }
  const cwd = row.cwd || '';
  for (const pr of projectRoots) {
    if (cwd === pr.path || cwd.startsWith(pr.path + '/')) {
      return pr.projectName;
    }
  }
  if (cwd.includes('/worktrees/')) {
    const m = cwd.match(/\/worktrees\/([^/]+)/);
    if (m) return m[1];
  }
  if (cwd && cwd !== '/' && cwd !== '/private/tmp' && cwd !== '/tmp') {
    return path.basename(cwd);
  }
  return cwd || '未分类项目';
}

function extractTextFromItem(itemType, itemJson) {
  if (!itemJson) return '';
  try {
    const obj = JSON.parse(itemJson);
    if (itemType === 'agentMessage' || itemType === 'plan') {
      return typeof obj.text === 'string' ? obj.text : '';
    }
    if (itemType === 'userMessage') {
      if (Array.isArray(obj.content)) {
        return obj.content
          .filter((c) => c && (c.type === 'text' || typeof c.text === 'string'))
          .map((c) => c.text || '')
          .join('\n');
      }
      return typeof obj.text === 'string' ? obj.text : '';
    }
    if (itemType === 'commandExecution') {
      return `$ ${obj.command || ''}${obj.status ? ` [${obj.status}]` : ''}`;
    }
    if (itemType === 'fileChange') {
      const files = Array.isArray(obj.changes)
        ? obj.changes.map((c) => `${c.kind?.type || 'edit'}: ${c.path || ''}`)
        : [];
      return files.join('\n');
    }
    if (itemType === 'reasoning') {
      if (Array.isArray(obj.summary) && obj.summary.length) {
        return obj.summary.join(' / ');
      }
      return '';
    }
  } catch {
    return '';
  }
  return '';
}

function computeEffectiveStatus({ thread, goal, latestTurn, dispatchTask }) {
  const dispatchTerminal =
    dispatchTask &&
    ['completed', 'failed', 'cleaned', 'cancelled', 'timed_out', 'stopped'].includes(
      dispatchTask.status
    );

  if (latestTurn?.status === 'inProgress' && !dispatchTerminal) {
    return { code: 'running', label: '运行中', tone: 'info' };
  }
  if (goal?.status === 'blocked') {
    return { code: 'blocked', label: 'Goal 阻塞', tone: 'warning' };
  }
  if (goal?.status === 'usage_limited' || goal?.status === 'budget_limited') {
    return { code: 'limited', label: '额度受限', tone: 'danger' };
  }
  if (goal?.status === 'active') {
    return { code: 'goal_active', label: 'Goal 进行中', tone: 'info' };
  }
  if (goal?.status === 'paused') {
    return { code: 'paused', label: 'Goal 暂停', tone: 'muted' };
  }
  if (goal?.status === 'complete') {
    return { code: 'complete', label: 'Goal 完成', tone: 'success' };
  }
  if (
    (!dispatchTerminal && latestTurn?.status === 'failed') ||
    dispatchTask?.status === 'failed' ||
    dispatchTask?.status === 'timed_out'
  ) {
    return { code: 'failed', label: '执行异常', tone: 'danger' };
  }
  if (dispatchTask?.status === 'cleaned') {
    return {
      code: 'exec_done',
      label: dispatchTask.exit_code === 124 ? '已清理(曾超时)' : 'CLI 已清理',
      tone: 'muted',
    };
  }
  if (thread.archived) {
    return { code: 'archived', label: '已归档', tone: 'muted' };
  }
  if (thread.source === 'exec') {
    return { code: 'exec_done', label: 'CLI 已完成', tone: 'success' };
  }
  return { code: 'idle', label: '就绪', tone: 'muted' };
}

export class CodexStore {
  constructor(consoleDb) {
    this.consoleDb = consoleDb;
    this.stateDbPath = path.join(CODEX_HOME, 'state_5.sqlite');
    this.goalsDbPath = path.join(CODEX_HOME, 'goals_1.sqlite');
    this.queueDbPath = path.join(CODEX_HOME, 'queue_1.sqlite');
    this.historyDbPath = path.join(CODEX_HOME, 'thread_history_1.sqlite');
  }

  getHealth() {
    return {
      codexHome: CODEX_HOME,
      stateDbExists: fs.existsSync(this.stateDbPath),
      goalsDbExists: fs.existsSync(this.goalsDbPath),
      queueDbExists: fs.existsSync(this.queueDbPath),
      historyDbExists: fs.existsSync(this.historyDbPath),
      dispatchStateExists: fs.existsSync(path.join(DISPATCH_STATE_DIR, 'state.json')),
    };
  }

  resolveThreadId(input) {
    if (typeof input !== 'string' || input.length < 4 || input.length > 256 || input.includes('\0')) throw new Error('Invalid thread ID');
    const errors = [];
    const matches = withReadOnlyDb(this.stateDbPath, db => {
      const exact = db.prepare('SELECT id FROM threads WHERE id = ?').get(input);
      if (exact) return [exact];
      return db.prepare('SELECT id FROM threads WHERE substr(id,1,length(?)) = ? ORDER BY id LIMIT 2').all(input,input);
    }, [], errors);
    if (errors.length) throw new Error('State database unavailable: '+errors[0].code);
    if (matches.length > 1) throw new Error('Ambiguous thread ID prefix; use full ID');
    return matches[0]?.id || null;
  }

  getThread(input) {
    const id = this.resolveThreadId(input);
    if (!id) return null;
    const snap = this.getSnapshot({ threadId:id, limit:1, includeManagedAgents:false });
    if (!snap.connected) throw new Error('State database unavailable');
    return snap.tasks.find(t => t.id === id) || null;
  }

  getSnapshot({ limit = 160, threadId = null, includeChildren = false, includeManagedAgents = true } = {}) {
    const errors = [];
    const prefsMap = this.consoleDb.getAllPrefs();
    const dispatchState = readDispatchState(errors);
    const dispatchTasksList = Object.values(dispatchState.tasks || {});
    const dispatchBySession = new Map();
    for (const t of dispatchTasksList) {
      if (t.session_id) dispatchBySession.set(t.session_id, t);
    }

    // 1. Read state_5.sqlite
    const stateData = withReadOnlyDb(
      this.stateDbPath,
      (db) => {
        const projects = db.prepare('SELECT id, name FROM projects ORDER BY position ASC').all();
        const roots = db.prepare(`
          SELECT pr.project_id, pr.path, p.name AS project_name
          FROM project_roots pr
          JOIN projects p ON p.id = pr.project_id
        `).all();
        const threadSelect = `
          SELECT id, rollout_path, created_at, updated_at, created_at_ms, updated_at_ms,
                 source, thread_source, originator, cwd, title, name, preview,
                 tokens_used, archived, is_pinned, git_branch, git_sha,
                 model, reasoning_effort, agent_nickname, agent_role, agent_path,
                 project_id, history_mode
          FROM threads`;
        const threads = threadId === null
          ? db.prepare(threadSelect+' ORDER BY updated_at DESC LIMIT ?').all(limit)
          : includeChildren
            ? db.prepare(threadSelect+' WHERE id = ? OR id IN (SELECT child_thread_id FROM thread_spawn_edges WHERE parent_thread_id = ?) ORDER BY CASE WHEN id = ? THEN 0 ELSE 1 END, updated_at DESC LIMIT ?').all(threadId,threadId,threadId,limit)
            : db.prepare(threadSelect+' WHERE id = ?').all(threadId);
        const totalRow = db.prepare('SELECT COUNT(*) AS c FROM threads').get();
        const spawnEdges = db.prepare(
          'SELECT parent_thread_id, child_thread_id, status FROM thread_spawn_edges'
        ).all();
        return { projects, roots, threads, totalThreads: totalRow?.c || threads.length, spawnEdges };
      },
      { projects: [], roots: [], threads: [], totalThreads: 0, spawnEdges: [] }, errors
    );

    const projectsById = new Map(stateData.projects.map((p) => [p.id, p.name]));
    const projectRoots = stateData.roots
      .map((r) => ({ path: r.path, projectName: r.project_name }))
      .sort((a, b) => b.path.length - a.path.length);

    const spawnByChild = new Map();
    const childrenByParent = new Map();
    for (const edge of stateData.spawnEdges) {
      spawnByChild.set(edge.child_thread_id, edge);
      const list = childrenByParent.get(edge.parent_thread_id) || [];
      list.push(edge);
      childrenByParent.set(edge.parent_thread_id, list);
    }

    // 2. Read goals_1.sqlite
    const goalsMap = withReadOnlyDb(
      this.goalsDbPath,
      (db) => {
        const rows = db.prepare('SELECT * FROM thread_goals').all();
        return new Map(rows.map((r) => [r.thread_id, r]));
      },
      new Map(), errors
    );

    // 3. Read queue_1.sqlite
    const queueCountMap = withReadOnlyDb(
      this.queueDbPath,
      (db) => {
        const rows = db.prepare(
          'SELECT thread_id, COUNT(*) AS cnt FROM queued_items GROUP BY thread_id'
        ).all();
        return new Map(rows.map((r) => [r.thread_id, r.cnt]));
      },
      new Map(), errors
    );

    // 4. Read latest turn + latest agent reply in thread_history_1.sqlite for loaded threads
    const threadIds = stateData.threads.map((t) => t.id);
    const { latestTurnMap, durationMap, latestReplyMap } = this._fetchThreadActivityBatch(threadIds, errors);

    // 5. Read console ops & collab bindings
    const recentOps = this.consoleDb.listOps({ limit: 80 });
    const opsByThread = new Map();
    for (const op of recentOps) {
      if (!op.threadId) continue;
      const arr = opsByThread.get(op.threadId) || [];
      arr.push(op);
      opsByThread.set(op.threadId, arr);
    }

    const bindings = this.consoleDb.listBindings({ limit: 200 });
    const bindingsByThread = new Map();
    for (const b of bindings) {
      if (!b.threadId) continue;
      const arr = bindingsByThread.get(b.threadId) || [];
      arr.push(b);
      bindingsByThread.set(b.threadId, arr);
    }

    // 6. Assemble unified task cards
    const tasks = stateData.threads.map((row) => {
      const pref = prefsMap.get(row.id) || null;
      const goal = goalsMap.get(row.id) || null;
      const dispatchTask = dispatchBySession.get(row.id) || null;
      const latestTurn = latestTurnMap.get(row.id) || null;
      const subMeta = parseSubagentMeta(row);
      const spawnEdge = spawnByChild.get(row.id) || null;
      const isSubagent = subMeta.isSubagent || Boolean(spawnEdge);
      const childEdges = childrenByParent.get(row.id) || [];

      const projectName = deriveProjectName(row, projectsById, projectRoots, dispatchTask);
      const worktreeLabel = parseWorktreeLabel(row.cwd || dispatchTask?.worktree_path);
      const status = computeEffectiveStatus({ thread: row, goal, latestTurn, dispatchTask });
      const updatedMs = row.updated_at_ms || (row.updated_at ? row.updated_at * 1000 : Date.now());
      const createdMs = row.created_at_ms || (row.created_at ? row.created_at * 1000 : updatedMs);
      const durationSec = goal?.time_used_seconds
        ? Number(goal.time_used_seconds)
        : Math.round((durationMap.get(row.id) || Math.max(0, updatedMs - createdMs)) / 1000);

      const pinned = pref ? pref.pinned : Boolean(row.is_pinned);
      const title = cleanDisplayTitle({
        customTitle: pref?.customTitle,
        threadName: row.name,
        dispatchTask,
        rawTitle: row.title,
        preview: row.preview,
        agentNickname: subMeta.nickname || row.agent_nickname,
        agentPath: subMeta.agentPath,
        id: row.id,
      });

      const latestReplyRaw = unwrapStructuredReply(latestReplyMap.get(row.id) || row.preview || '');
      const latestReply = latestReplyRaw.replace(/\s+/g, ' ').trim().slice(0, 220);
      const threadBindings = bindingsByThread.get(row.id) || [];
      const threadOps = opsByThread.get(row.id) || [];

      const isManagedDispatch =
        Boolean(dispatchTask) ||
        (row.git_branch || '').startsWith('agy-worker/') ||
        (row.cwd || '').includes('multi-agent-dispatch');
      const isExec = row.source === 'exec' || row.originator === 'codex_exec' || isManagedDispatch;

      return {
        id: row.id,
        shortId: row.id.slice(0, 8),
        title,
        customTitle: pref?.customTitle || null,
        rawTitle: (row.title || '').slice(0, 400),
        projectName,
        worktreeLabel,
        cwd: row.cwd || '',
        branch: row.git_branch || dispatchTask?.branch || '',
        model: row.model || dispatchTask?.model || '',
        reasoningEffort: row.reasoning_effort || dispatchTask?.effort || '',
        source: row.source || '',
        originator: row.originator || '',
        isExec,
        isManagedDispatch,
        isAgyDispatched: isExec,
        isSubagent,
        parentThreadId: subMeta.parentThreadId || spawnEdge?.parent_thread_id || null,
        childCount: childEdges.length,
        agentNickname: subMeta.nickname || row.agent_nickname || null,
        agentRole: row.agent_role || null,
        pinned,
        pinnedAt: pref?.pinnedAt || null,
        hidden: Boolean(pref?.hidden),
        archived: Boolean(row.archived),
        tokensUsed: Number(goal?.tokens_used || row.tokens_used || 0),
        durationSec,
        createdAtMs: createdMs,
        updatedAtMs: updatedMs,
        status,
        goal: goal
          ? {
              goalId: goal.goal_id,
              objective: goal.objective,
              status: goal.status,
              tokenBudget: goal.token_budget,
              tokensUsed: goal.tokens_used,
              timeUsedSeconds: goal.time_used_seconds,
              updatedAtMs: goal.updated_at_ms,
            }
          : null,
        queuedCount: queueCountMap.get(row.id) || 0,
        latestReply,
        latestTurnStatus: latestTurn?.status || null,
        dispatchTask: dispatchTask
          ? {
              taskId: dispatchTask.task_id,
              status: dispatchTask.status,
              difficulty: dispatchTask.difficulty,
              branch: dispatchTask.branch,
              worktreePath: dispatchTask.worktree_path,
              repoRoot: dispatchTask.repo_root,
              isolation: dispatchTask.isolation,
              sandbox: dispatchTask.sandbox,
              exitCode: dispatchTask.exit_code,
            }
          : null,
        bindingCount: threadBindings.length,
        changeKeys: threadBindings.map((b) => b.changeKey),
        runningOpsCount: threadOps.filter((o) => o.status === 'running').length,
      };
    });

    // 7. Build managed subagents view (dispatch workers + active console spawns + codex subagents)
    const managedAgents = (includeManagedAgents ? dispatchTasksList : [])
      .map((t) => {
        const result = readDispatchRunResult(t.run_dir);
        const linkedThread = tasks.find((x) => x.id === t.session_id) || null;
        return {
          kind: 'dispatch',
          id: t.task_id,
          taskId: t.task_id,
          threadId: t.session_id || null,
          title: linkedThread?.title || `${path.basename(t.repo_root || t.original_cwd || '')} · ${t.task_id}`,
          projectName: t.repo_root ? path.basename(t.repo_root) : path.basename(t.original_cwd || ''),
          status: linkedThread?.status?.code === 'running' ? 'running' : (t.status || 'unknown'),
          model: t.model || linkedThread?.model || '',
          effort: t.effort || '',
          difficulty: t.difficulty || '',
          branch: t.branch || '',
          worktreePath: t.worktree_path || t.workdir || '',
          repoRoot: t.repo_root || t.original_cwd || '',
          isolation: t.isolation || '',
          sandbox: t.sandbox || '',
          exitCode: t.exit_code ?? null,
          createdAt: t.created_at,
          updatedAt: t.updated_at,
          tokensUsed: linkedThread?.tokensUsed || 0,
          summary:
            result?.report?.summary ||
            result?.summary ||
            linkedThread?.latestReply ||
            '',
          changedFiles: result?.report?.files_modified || result?.changed_files || [],
          verificationPassed: result?.verification_status === 'passed' && result?.verification_passed === true,
          verificationStatus: result?.verification_status || 'unknown',
          risks: result?.report?.risks_or_followups || [],
          worktreeExists: t.worktree_path ? fs.existsSync(t.worktree_path) : false,
        };
      })
      .sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));

    const nonSubagentTasks = tasks.filter((t) => !t.isSubagent);
    const stats = {
      totalThreads: stateData.totalThreads,
      loadedThreads: tasks.length,
      visibleThreads: nonSubagentTasks.length,
      agyCount: nonSubagentTasks.filter((t) => t.isAgyDispatched).length,
      execCount: tasks.filter((t) => t.isExec).length,
      runningCount: tasks.filter((t) => t.status.code === 'running').length,
      goalBlockedCount: tasks.filter((t) => t.status.code === 'blocked').length,
      goalActiveCount: tasks.filter((t) => t.status.code === 'goal_active').length,
      pinnedCount: tasks.filter((t) => t.pinned).length,
      managedCount: managedAgents.length,
      subagentThreadCount: tasks.filter((t) => t.isSubagent).length,
      collabCount: bindings.length,
      runningOpsCount: recentOps.filter((o) => o.status === 'running').length,
    };

    const projects = [...new Set(tasks.map((t) => t.projectName).filter(Boolean))].sort();
    const worktrees = [...new Set(tasks.map((t) => t.worktreeLabel).filter(Boolean))].sort();

    return {
      connected: !errors.some(e=>e.source==='state_5.sqlite'),
      health: { ...this.getHealth(), errors },
      stats,
      filters: { projects, worktrees },
      tasks,
      managedAgents,
      bindings,
      recentOps: recentOps.slice(0, 25),
      fetchedAt: Date.now(),
    };
  }

  _fetchThreadActivityBatch(threadIds, errors = []) {
    const latestTurnMap = new Map();
    const durationMap = new Map();
    const latestReplyMap = new Map();
    if (!threadIds.length) return { latestTurnMap, durationMap, latestReplyMap };

    withReadOnlyDb(
      this.historyDbPath,
      (db) => {
        const placeholders = threadIds.map(() => '?').join(',');
        // Latest turn per thread + total duration
        const turnRows = db.prepare(`
          SELECT thread_id, turn_id, status, started_at, completed_at, duration_ms, rollout_ordinal
          FROM thread_turns
          WHERE thread_id IN (${placeholders})
          ORDER BY thread_id, rollout_ordinal DESC
        `).all(...threadIds);

        for (const row of turnRows) {
          if (!latestTurnMap.has(row.thread_id)) {
            latestTurnMap.set(row.thread_id, row);
          }
          if (row.duration_ms) {
            durationMap.set(row.thread_id, (durationMap.get(row.thread_id) || 0) + Number(row.duration_ms));
          }
        }

        // Latest agentMessage per thread (window via subquery on max rollout_ordinal)
        const replyRows = db.prepare(`
          SELECT ti.thread_id, ti.item_json
          FROM thread_items ti
          INNER JOIN (
            SELECT thread_id, MAX(rollout_ordinal) AS max_ord
            FROM thread_items
            WHERE thread_id IN (${placeholders}) AND item_type = 'agentMessage'
            GROUP BY thread_id
          ) latest
            ON ti.thread_id = latest.thread_id AND ti.rollout_ordinal = latest.max_ord
          WHERE ti.item_type = 'agentMessage'
        `).all(...threadIds);

        for (const r of replyRows) {
          const text = extractTextFromItem('agentMessage', r.item_json);
          if (text) latestReplyMap.set(r.thread_id, text);
        }
      },
      null, errors
    );

    return { latestTurnMap, durationMap, latestReplyMap };
  }

  // Compact model-facing reads never enumerate unrelated run artifacts.
  getManagedTask(taskId, includeResult = false) {
    if (typeof taskId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(taskId)) throw new Error('Invalid task ID');
    const errors = [];
    const state = readDispatchState(errors);
    if (errors.length) throw new Error('Dispatcher state unavailable');
    if (!Object.hasOwn(state.tasks, taskId)) return null;
    const task = state.tasks[taskId];
    if (!task || task.task_id !== taskId) throw new Error('Invalid task record');
    let result = null;
    if (includeResult && task.run_dir) {
      const expected = path.resolve(DISPATCH_STATE_DIR, 'runs', taskId);
      // Never follow a record to arbitrary paths or symlink/junction targets.
      try {
        const actual = fs.realpathSync(expected);
        const root = fs.realpathSync(DISPATCH_STATE_DIR);
        const canonical = path.join(root, 'runs', taskId);
        if (path.resolve(task.run_dir) !== expected || actual !== canonical ||
            fs.lstatSync(expected).isSymbolicLink()) throw new Error('Unexpected run directory');
        const ref = task.result_ref;
        // No inference from directory ordering or old artifacts. Only the
        // state-published result of the current completed turn is eligible.
        if (!['completed','failed','partial','blocked','timed_out'].includes(task.status)
            || task.active_turn_id || !ref || !/^[a-f0-9]{64}$/.test(ref.sha256)
            || !(ref.turn === null || (typeof ref.turn === 'string' && /^turn-[A-Za-z0-9_-]+$/.test(ref.turn)))) throw new Error('No current result reference');
        const latest = path.join(expected, ...(ref.turn === null ? [] : [ref.turn]), 'result.json');
        const stat = fs.lstatSync(latest);
        if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 262144 ||
            fs.realpathSync(latest) !== path.join(actual,path.relative(expected,latest))) throw new Error('Invalid result artifact');
        const bytes = fs.readFileSync(latest);
        if (bytes.length > 262144 || crypto.createHash('sha256').update(bytes).digest('hex') !== ref.sha256) throw new Error('Result digest mismatch');
        const candidate = JSON.parse(bytes.toString('utf8'));
        if (candidate?.task_id !== taskId || (candidate.turn_id ?? null) !== ref.turn ||
            candidate.session_id !== task.session_id || candidate.exit_code !== task.exit_code ||
            candidate.task_status !== task.task_status || !candidate.report ||
            candidate.report.status !== candidate.task_status) throw new Error('Result identity mismatch');
        result = candidate;
      } catch {
        // Missing, unsafe, incompatible and oversized artifacts are not verified.
        result = null;
      }
    }
    return {task,result};
  }


  // Read only the producer's bounded metadata snapshot; not raw output.
  getTaskEvents(taskId, turnId, cursor=0, limit=10) {
    const entry=this.getManagedTask(taskId,false);
    if (!entry || entry.task.stream_events!==true) throw new Error('Streaming task unavailable');
    const task=entry.task;
    if (!Number.isSafeInteger(cursor)||cursor<0||!Number.isInteger(limit)||limit<1||limit>10) throw new Error('Invalid cursor');
    if (cursor>0 && turnId==null) throw new Error('Resume cursor requires turnId');
    const current=task.active_turn_id || task.result_ref?.turn || 'initial';
    const turn=turnId ?? current;
    if (!(turn==='initial'||(typeof turn==='string'&&/^turn-[A-Za-z0-9_-]{1,75}$/.test(turn)))) throw new Error('Invalid turn');
    const expected=path.resolve(DISPATCH_STATE_DIR,'runs',taskId);
    if (path.resolve(task.run_dir)!==expected) throw new Error('Invalid run directory');
    const root=fs.realpathSync(DISPATCH_STATE_DIR);
    const directory=path.join(expected,...(turn==='initial'?[]:[turn]));
    const file=path.join(directory,'stream-state.json');
    const canonical=path.join(root,'runs',taskId,...(turn==='initial'?[]:[turn]),'stream-state.json');
    if (fs.realpathSync(file)!==canonical||fs.lstatSync(file).isSymbolicLink()) throw new Error('Unsafe stream path');
    const fd=fs.openSync(file,'r');
    let parsed;
    try {
      const stat=fs.fstatSync(fd);
      if (!stat.isFile()||stat.size>16384) throw new Error('Invalid stream snapshot');
      const bytes=Buffer.alloc(16385);
      let n=0;
      while(n<bytes.length) {
        const m=fs.readSync(fd,bytes,n,bytes.length-n,null);
        if (!m) break;
        n+=m;
      }
      if(n>16384) throw new Error('Oversize snapshot');
      parsed=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,n)));
    } finally {fs.closeSync(fd);}
    const entries=parsed?.entries;
    if (![1,2].includes(parsed?.version)||parsed.taskId!==taskId||parsed.turnId!==turn||
        !Array.isArray(entries)||entries.length<1||entries.length>64) throw new Error('Invalid snapshot identity');
    const taskSequence=parsed.version===2;
    if(taskSequence&&(!Number.isSafeInteger(parsed.sequenceBase)||parsed.sequenceBase<0||
       !['task','since_upgrade'].includes(parsed.sequenceScope)||
       (turn==='initial'&&(parsed.sequenceBase!==0||parsed.sequenceScope!=='task'))))throw new Error('Invalid task sequence scope');
    const kinds=['queued','running','progress','heartbeat','process_exit','timed_out','stream_failed','launch_failed','interrupted'];
    let last=0, previous=null;
    const clean=entries.map(e=>{
      if (!e||!Number.isSafeInteger(e.seq)||e.seq<=0||(last&&e.seq!==last+1)||
          (taskSequence&&(!Number.isSafeInteger(e.taskSeq)||e.taskSeq!==parsed.sequenceBase+e.seq))||
          !kinds.includes(e.kind)||!Number.isSafeInteger(e.at)||e.at<0||
          !Number.isSafeInteger(e.stdoutBytes)||e.stdoutBytes<0||e.stdoutBytes>4194304||
          !Number.isSafeInteger(e.stderrBytes)||e.stderrBytes<0||e.stderrBytes>1048576||
          !Number.isSafeInteger(e.lines)||e.lines<0||e.lines>e.stdoutBytes||
          (previous&&(previous.stdoutBytes>e.stdoutBytes||previous.stderrBytes>e.stderrBytes||previous.lines>e.lines||
            ['process_exit','timed_out','stream_failed','launch_failed','interrupted'].includes(previous.kind)))) throw new Error('Invalid stream sequence');
      last=e.seq;previous=e;
      return {seq:e.seq,...(taskSequence?{taskSeq:e.taskSeq}:{}),kind:e.kind,at:e.at,stdoutBytes:e.stdoutBytes,stderrBytes:e.stderrBytes,lines:e.lines};
    });
    if(cursor>last) throw new Error('Cursor ahead of producer');
    const gap=cursor<clean[0].seq-1;
    const available=clean.filter(e=>e.seq>cursor);
    const page=available.slice(0,limit);
    return {taskId,turnId:turn,taskStatus:typeof task.status==='string'&&/^[a-z_]{1,24}$/.test(task.status)?task.status:'unknown',
      current:turn===current,gap,entries:page,nextCursor:page.at(-1)?.seq??cursor,hasMore:available.length>limit,
      ...(taskSequence?{sequenceScope:parsed.sequenceScope}:{}),verification:'unknown'};
  }

  getLogPage(input, cursor = 0, limit = 10) {
    const id = this.resolveThreadId(input);
    if (!id) throw new Error('Thread not found');
    if (!Number.isSafeInteger(cursor) || cursor < 0 || !Number.isInteger(limit) || limit < 1 || limit > 20) throw new Error('Invalid log pagination');
    const errors = [];
    // Explicit metadata-only page; no arbitrary files, prompts or raw command output.
    const rows = withReadOnlyDb(this.historyDbPath, db => db.prepare(
      'SELECT rowid AS cursor, item_type, created_at_ms FROM thread_items WHERE thread_id = ? AND rowid > ? ORDER BY rowid LIMIT ?'
    ).all(id,cursor,limit+1), [], errors);
    if (errors.length) throw new Error('History database unavailable');
    const entries = rows.slice(0,limit).map(r=>({cursor:r.cursor,type:typeof r.item_type==='string' ? r.item_type.slice(0,40) : 'unknown',at:r.created_at_ms ?? null}));
    return {entries,nextCursor:entries.at(-1)?.cursor ?? cursor,hasMore:rows.length>limit};
  }

  getThreadDetail(input) {
    const threadId = this.resolveThreadId(input);
    if (!threadId) return {task:null,turns:[],messages:[],queuedItems:[],childThreads:[],ops:[],bindings:[],errors:[]};
    const snapshot = this.getSnapshot({ threadId, includeChildren:true, limit:251 });
    if (!snapshot.connected) throw new Error('State database unavailable');
    const errors = [...snapshot.health.errors];
    const task = snapshot.tasks.find((t) => t.id === threadId) || null;

    const history = withReadOnlyDb(
      this.historyDbPath,
      (db) => {
        const turns = db.prepare(`
          SELECT turn_id, rollout_ordinal, status, started_at, completed_at, duration_ms, error_json
          FROM thread_turns
          WHERE thread_id = ?
          ORDER BY rollout_ordinal DESC
          LIMIT 20
        `).all(threadId);

        const items = db.prepare(`
          SELECT turn_id, item_id, rollout_ordinal, created_at_ms, item_type, item_json
          FROM thread_items
          WHERE thread_id = ?
            AND item_type IN ('userMessage', 'agentMessage', 'fileChange', 'commandExecution', 'plan', 'reasoning')
          ORDER BY rollout_ordinal DESC
          LIMIT 80
        `).all(threadId);

        const messages = items
          .reverse()
          .map((it) => {
            const text = extractTextFromItem(it.item_type, it.item_json);
            return {
              id: it.item_id,
              turnId: it.turn_id,
              ordinal: it.rollout_ordinal,
              type: it.item_type,
              createdAtMs: it.created_at_ms,
              text: text.length > 4000 ? `${text.slice(0, 4000)}\n…(已截断)` : text,
            };
          })
          .filter((m) => m.text && m.text.trim());

        return { turns, messages };
      },
      { turns: [], messages: [] }, errors
    );

    const queuedItems = withReadOnlyDb(
      this.queueDbPath,
      (db) => {
        return db.prepare(`
          SELECT id, payload_json, queue_order, created_at_ms
          FROM queued_items
          WHERE thread_id = ?
          ORDER BY queue_order ASC
        `).all(threadId);
      },
      [], errors
    );

    const childThreads = snapshot.tasks
      .filter((t) => t.parentThreadId === threadId)
      .map((t) => ({
        id: t.id,
        shortId: t.shortId,
        title: t.title,
        status: t.status,
        updatedAtMs: t.updatedAtMs,
      }));

    const ops = this.consoleDb.listOps({ threadId, limit: 25 });
    const bindings = this.consoleDb.listBindings({ threadId, limit: 20 });

    return {
      task,
      errors,
      turns: history.turns,
      messages: history.messages,
      queuedItems,
      childThreads,
      ops,
      bindings,
    };
  }
}
