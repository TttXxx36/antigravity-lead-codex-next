import { DatabaseSync } from 'node:sqlite';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export class ConsoleDB {
  constructor(dataDir) {
    fs.mkdirSync(dataDir, { recursive: true });
    this.dbPath = path.join(dataDir, 'console.sqlite');
    this.db = new DatabaseSync(this.dbPath);
    this.db.exec(`
      PRAGMA journal_mode = WAL;
      PRAGMA busy_timeout = 3000;
      PRAGMA synchronous = NORMAL;

      CREATE TABLE IF NOT EXISTS thread_prefs (
        thread_id TEXT PRIMARY KEY,
        pinned INTEGER NOT NULL DEFAULT 0,
        pinned_at INTEGER,
        hidden INTEGER NOT NULL DEFAULT 0,
        custom_title TEXT,
        updated_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS console_ops (
        id TEXT PRIMARY KEY,
        thread_id TEXT,
        op_type TEXT NOT NULL,
        prompt TEXT NOT NULL,
        mode TEXT,
        status TEXT NOT NULL,
        output_text TEXT,
        error_text TEXT,
        meta_json TEXT,
        dedup_key TEXT,
        started_at INTEGER NOT NULL,
        finished_at INTEGER,
        duration_ms INTEGER
      );
      CREATE INDEX IF NOT EXISTS idx_console_ops_thread ON console_ops(thread_id, started_at DESC);
      CREATE INDEX IF NOT EXISTS idx_console_ops_started ON console_ops(started_at DESC);

      CREATE TABLE IF NOT EXISTS collab_bindings (
        id TEXT PRIMARY KEY,
        change_key TEXT NOT NULL,
        goal_title TEXT NOT NULL,
        thread_id TEXT,
        task_id TEXT,
        owner_role TEXT NOT NULL DEFAULT 'codex',
        status TEXT NOT NULL DEFAULT 'active',
        repo_path TEXT,
        branch TEXT,
        notes TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_collab_bindings_thread ON collab_bindings(thread_id);
      CREATE INDEX IF NOT EXISTS idx_collab_bindings_updated ON collab_bindings(updated_at DESC);

      CREATE TABLE IF NOT EXISTS collab_messages (
        id TEXT PRIMARY KEY,
        binding_id TEXT,
        thread_id TEXT,
        direction TEXT NOT NULL DEFAULT 'note',
        author TEXT NOT NULL DEFAULT 'antigravity',
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_collab_messages_binding ON collab_messages(binding_id, created_at DESC);
    `);

    // Safe schema migration for existing console.sqlite databases
    try {
      this.db.exec('ALTER TABLE thread_prefs ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0');
    } catch {
      // column already exists
    }

    // Mark orphaned running ops from previous server lifetime as interrupted
    const now = Date.now();
    this.db.prepare(`
      UPDATE console_ops
      SET status = 'interrupted',
          error_text = COALESCE(error_text, 'MCP 服务重启，后台任务已中断'),
          finished_at = COALESCE(finished_at, ?)
      WHERE status = 'running'
    `).run(now);
  }

  getAllPrefs() {
    const rows = this.db.prepare(`
      SELECT thread_id, pinned, pinned_at, hidden, custom_title, updated_at
      FROM thread_prefs
    `).all();
    const map = new Map();
    for (const row of rows) {
      map.set(row.thread_id, {
        pinned: Boolean(row.pinned),
        pinnedAt: row.pinned_at ?? null,
        hidden: Boolean(row.hidden),
        customTitle: row.custom_title ?? null,
        updatedAt: row.updated_at,
      });
    }
    return map;
  }

  setThreadPref(threadId, { pinned, hidden, customTitle }) {
    const now = Date.now();
    const existing = this.db.prepare(
      'SELECT pinned, pinned_at, hidden, custom_title FROM thread_prefs WHERE thread_id = ?'
    ).get(threadId);

    const nextHidden = hidden !== undefined ? (hidden ? 1 : 0) : (existing?.hidden ?? 0);
    // Hiding a thread automatically unpins it so it moves cleanly into the hidden drawer
    const nextPinned =
      hidden === true
        ? 0
        : pinned !== undefined
          ? (pinned ? 1 : 0)
          : (existing?.pinned ?? 0);
    const nextPinnedAt =
      nextPinned === 0
        ? null
        : pinned !== undefined
          ? now
          : (existing?.pinned_at ?? now);
    const nextTitle = customTitle !== undefined
      ? (customTitle && customTitle.trim() ? customTitle.trim() : null)
      : (existing?.custom_title ?? null);

    this.db.prepare(`
      INSERT INTO thread_prefs (thread_id, pinned, pinned_at, hidden, custom_title, updated_at)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(thread_id) DO UPDATE SET
        pinned = excluded.pinned,
        pinned_at = excluded.pinned_at,
        hidden = excluded.hidden,
        custom_title = excluded.custom_title,
        updated_at = excluded.updated_at
    `).run(threadId, nextPinned, nextPinnedAt, nextHidden, nextTitle, now);

    return {
      threadId,
      pinned: Boolean(nextPinned),
      pinnedAt: nextPinnedAt,
      hidden: Boolean(nextHidden),
      customTitle: nextTitle,
    };
  }

  makeDedupKey(threadId, mode, prompt) {
    return crypto
      .createHash('sha256')
      .update(`${threadId || ''}::${mode || ''}::${(prompt || '').trim()}`)
      .digest('hex')
      .slice(0, 24);
  }

  findRecentDuplicate(dedupKey, windowMs = 60_000) {
    const cutoff = Date.now() - windowMs;
    return this.db.prepare(`
      SELECT id, status, started_at
      FROM console_ops
      WHERE dedup_key = ? AND started_at >= ? AND status IN ('running', 'succeeded')
      ORDER BY started_at DESC
      LIMIT 1
    `).get(dedupKey, cutoff) || null;
  }

  createOp({ threadId = null, opType, prompt, mode = null, meta = null, dedupKey = null }) {
    const id = `op_${Date.now().toString(36)}_${crypto.randomBytes(4).toString('hex')}`;
    const now = Date.now();
    this.db.prepare(`
      INSERT INTO console_ops (id, thread_id, op_type, prompt, mode, status, meta_json, dedup_key, started_at)
      VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)
    `).run(id, threadId, opType, prompt, mode, meta ? JSON.stringify(meta) : null, dedupKey, now);
    return this.getOp(id);
  }

  finishOp(id, { status, outputText = null, errorText = null, metaPatch = null }) {
    const now = Date.now();
    const cur = this.db.prepare('SELECT started_at, meta_json FROM console_ops WHERE id = ?').get(id);
    if (!cur) return null;
    let nextMeta = cur.meta_json;
    if (metaPatch) {
      let parsed = {};
      try {
        parsed = cur.meta_json ? JSON.parse(cur.meta_json) : {};
      } catch {
        parsed = {};
      }
      nextMeta = JSON.stringify({ ...parsed, ...metaPatch });
    }
    const durationMs = Math.max(0, now - Number(cur.started_at || now));
    this.db.prepare(`
      UPDATE console_ops
      SET status = ?, output_text = ?, error_text = ?, meta_json = ?, finished_at = ?, duration_ms = ?
      WHERE id = ?
    `).run(status, outputText, errorText, nextMeta, now, durationMs, id);
    return this.getOp(id);
  }

  getOp(id) {
    const row = this.db.prepare('SELECT * FROM console_ops WHERE id = ?').get(id);
    return row ? this._formatOp(row) : null;
  }

  listOps({ threadId = null, limit = 30 } = {}) {
    const rows = threadId
      ? this.db.prepare(`
          SELECT * FROM console_ops WHERE thread_id = ? ORDER BY started_at DESC LIMIT ?
        `).all(threadId, limit)
      : this.db.prepare(`
          SELECT * FROM console_ops ORDER BY started_at DESC LIMIT ?
        `).all(limit);
    return rows.map((r) => this._formatOp(r));
  }

  _formatOp(row) {
    let meta = null;
    if (row.meta_json) {
      try {
        meta = JSON.parse(row.meta_json);
      } catch {
        meta = null;
      }
    }
    return {
      id: row.id,
      threadId: row.thread_id,
      opType: row.op_type,
      prompt: row.prompt,
      mode: row.mode,
      status: row.status,
      outputText: row.output_text || '',
      errorText: row.error_text || '',
      meta,
      startedAt: row.started_at,
      finishedAt: row.finished_at,
      durationMs: row.duration_ms,
    };
  }

  listBindings({ threadId = null, limit = 100 } = {}) {
    const rows = threadId
      ? this.db.prepare(`
          SELECT * FROM collab_bindings WHERE thread_id = ? ORDER BY updated_at DESC LIMIT ?
        `).all(threadId, limit)
      : this.db.prepare(`
          SELECT * FROM collab_bindings ORDER BY updated_at DESC LIMIT ?
        `).all(limit);

    const msgStmt = this.db.prepare(`
      SELECT * FROM collab_messages WHERE binding_id = ? ORDER BY created_at DESC LIMIT 10
    `);

    return rows.map((r) => ({
      id: r.id,
      changeKey: r.change_key,
      goalTitle: r.goal_title,
      threadId: r.thread_id,
      taskId: r.task_id,
      ownerRole: r.owner_role,
      status: r.status,
      repoPath: r.repo_path,
      branch: r.branch,
      notes: r.notes || '',
      createdAt: r.created_at,
      updatedAt: r.updated_at,
      messages: msgStmt.all(r.id).map((m) => ({
        id: m.id,
        bindingId: m.binding_id,
        threadId: m.thread_id,
        direction: m.direction,
        author: m.author,
        content: m.content,
        createdAt: m.created_at,
      })),
    }));
  }

  upsertBinding({
    id = null,
    changeKey,
    goalTitle,
    threadId = null,
    taskId = null,
    ownerRole = 'codex',
    status = 'active',
    repoPath = null,
    branch = null,
    notes = '',
  }) {
    const now = Date.now();
    const existing = id
      ? this.db.prepare('SELECT * FROM collab_bindings WHERE id = ?').get(id)
      : this.db.prepare(
          "SELECT * FROM collab_bindings WHERE change_key = ? AND COALESCE(thread_id, '') = COALESCE(?, '') LIMIT 1"
        ).get(changeKey, threadId || '');

    if (existing) {
      this.db.prepare(`
        UPDATE collab_bindings
        SET change_key = ?, goal_title = ?, thread_id = ?, task_id = ?,
            owner_role = ?, status = ?, repo_path = ?, branch = ?, notes = ?, updated_at = ?
        WHERE id = ?
      `).run(
        changeKey || existing.change_key,
        goalTitle || existing.goal_title,
        threadId !== undefined ? threadId : existing.thread_id,
        taskId !== undefined ? taskId : existing.task_id,
        ownerRole || existing.owner_role,
        status || existing.status,
        repoPath !== undefined ? repoPath : existing.repo_path,
        branch !== undefined ? branch : existing.branch,
        notes !== undefined ? notes : existing.notes,
        now,
        existing.id
      );
      return this.listBindings().find((b) => b.id === existing.id);
    }

    const newId = `bnd_${Date.now().toString(36)}_${crypto.randomBytes(4).toString('hex')}`;
    this.db.prepare(`
      INSERT INTO collab_bindings (
        id, change_key, goal_title, thread_id, task_id, owner_role,
        status, repo_path, branch, notes, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      newId,
      changeKey,
      goalTitle || changeKey,
      threadId,
      taskId,
      ownerRole,
      status,
      repoPath,
      branch,
      notes || '',
      now,
      now
    );
    return this.listBindings().find((b) => b.id === newId);
  }

  deleteBinding(id) {
    this.db.prepare('DELETE FROM collab_messages WHERE binding_id = ?').run(id);
    const res = this.db.prepare('DELETE FROM collab_bindings WHERE id = ?').run(id);
    return { deleted: res.changes > 0, id };
  }

  addCollabMessage({ bindingId = null, threadId = null, direction = 'note', author = 'antigravity', content }) {
    const id = `msg_${Date.now().toString(36)}_${crypto.randomBytes(4).toString('hex')}`;
    const now = Date.now();
    this.db.prepare(`
      INSERT INTO collab_messages (id, binding_id, thread_id, direction, author, content, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(id, bindingId, threadId, direction, author, content, now);
    if (bindingId) {
      this.db.prepare('UPDATE collab_bindings SET updated_at = ? WHERE id = ?').run(now, bindingId);
    }
    return { id, bindingId, threadId, direction, author, content, createdAt: now };
  }

  close() {
    try {
      this.db.close();
    } catch {
      // ignore
    }
  }
}
