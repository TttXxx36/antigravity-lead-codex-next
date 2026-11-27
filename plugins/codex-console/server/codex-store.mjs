import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { runtimePaths } from './platform.mjs';

const { codexHome: CODEX_HOME, dispatchStateDir: DISPATCH_STATE_DIR } = runtimePaths();

function withReadOnlyDb(dbFile, fn, fallback) {
  if (!fs.existsSync(dbFile)) return fallback;
  let db = null;
  try {
    db = new DatabaseSync(dbFile, { readOnly: true });
    db.exec('PRAGMA busy_timeout = 2000;');
    return fn(db);
  } catch {
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

function readDispatchState() {
  const statePath = path.join(DISPATCH_STATE_DIR, 'state.json');
  if (!fs.existsSync(statePath)) return { tasks: {} };
  try {
    const raw = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    return raw && typeof raw === 'object' ? raw : { tasks: {} };
  } catch {
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

  getSnapshot({ limit = 160 } = {}) {
    const prefsMap = this.consoleDb.getAllPrefs();
    const dispatchState = readDispatchState();
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
        const threads = db.prepare(`
          SELECT id, rollout_path, created_at, updated_at, created_at_ms, updated_at_ms,
                 source, thread_source, originator, cwd, title, name, preview,
                 tokens_used, archived, is_pinned, git_branch, git_sha,
                 model, reasoning_effort, agent_nickname, agent_role, agent_path,
                 project_id, history_mode
          FROM threads
          ORDER BY updated_at DESC
          LIMIT ?
        `).all(limit);
        const totalRow = db.prepare('SELECT COUNT(*) AS c FROM threads').get();
        const spawnEdges = db.prepare(
          'SELECT parent_thread_id, child_thread_id, status FROM thread_spawn_edges'
        ).all();
        return { projects, roots, threads, totalThreads: totalRow?.c || threads.length, spawnEdges };
      },
      { projects: [], roots: [], threads: [], totalThreads: 0, spawnEdges: [] }
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
      new Map()
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
      new Map()
    );

    // 4. Read latest turn + latest agent reply in thread_history_1.sqlite for loaded threads
    const threadIds = stateData.threads.map((t) => t.id);
    const { latestTurnMap, durationMap, latestReplyMap } = this._fetchThreadActivityBatch(threadIds);

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
    const managedAgents = dispatchTasksList
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
          verificationPassed: Boolean(result?.report?.verification_passed),
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
      connected: this.getHealth().stateDbExists,
      health: this.getHealth(),
      stats,
      filters: { projects, worktrees },
      tasks,
      managedAgents,
      bindings,
      recentOps: recentOps.slice(0, 25),
      fetchedAt: Date.now(),
    };
  }

  _fetchThreadActivityBatch(threadIds) {
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
      null
    );

    return { latestTurnMap, durationMap, latestReplyMap };
  }

  getThreadDetail(threadId) {
    const snapshot = this.getSnapshot({ limit: 200 });
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
      { turns: [], messages: [] }
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
      []
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
      turns: history.turns,
      messages: history.messages,
      queuedItems,
      childThreads,
      ops,
      bindings,
    };
  }
}
