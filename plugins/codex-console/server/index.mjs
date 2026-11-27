import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { ConsoleDB } from './console-db.mjs';
import { CodexStore } from './codex-store.mjs';
import { CodexRunner, DIAGNOSE_BLOCKER_PROMPT, buildExecEnv } from './runner.mjs';
import { QuotaTracker } from './quota.mjs';
import { compactReply, compactError, compactStatus, compactDelta, compactOperation } from './compact.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PLUGIN_ROOT = path.resolve(__dirname, '..');

function parseArgs(argv) {
  let dataDir = path.join(os.homedir(), '.local', 'state', 'codex-console');
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--data-dir' && argv[i + 1]) {
      dataDir = argv[++i];
    } else if (arg.startsWith('--data-dir=')) {
      dataDir = arg.slice('--data-dir='.length);
    } else if (arg.startsWith('--data_dir=')) {
      dataDir = arg.slice('--data_dir='.length);
    }
  }
  return { dataDir };
}

const { dataDir } = parseArgs(process.argv.slice(2));
const consoleDb = new ConsoleDB(dataDir);
const store = new CodexStore(consoleDb);
const runner = new CodexRunner(consoleDb);
const quotaTracker = new QuotaTracker({
  codexBin: runner.codexBin,
  env: buildExecEnv(),
});

const APP_URI = 'ui://codex-console/app.html';
const APP_MIME = 'text/html;profile=mcp-app';

const PANE_META = {
  ui: { resourceUri: APP_URI },
  'com.google.antigravity/ui': {
    entrypoints: [
      { type: 'aux_pane', title: 'Codex Console' },
      { type: 'global', title: 'Codex Console' },
    ],
  },
};

const APP_ONLY_META = {
  ui: { visibility: ['app'] },
};

const BOTH_META = {
  ui: { visibility: ['model', 'app'] },
};

// Metadata separates views; the actual host must honor visibility.
const LEGACY_DETAIL_META = process.env.ALC_LEGACY_MODEL_DETAIL === '1' ? BOTH_META : APP_ONLY_META;
const MODEL_META = { ui:{visibility:['model']} };

function readAppHtml() {
  const htmlPath = process.env.CODEX_CONSOLE_HTML || path.join(PLUGIN_ROOT, 'dist', 'app.html');
  if (!fs.existsSync(htmlPath)) {
    return `<!doctype html><html><body style="font-family:system-ui;padding:20px;background:#111318;color:#e5e7eb">
      <h3>Codex Console UI 未构建</h3>
      <p>请运行 <code>npm run build:ui</code> 生成 ${htmlPath}</p>
    </body></html>`;
  }
  return fs.readFileSync(htmlPath, 'utf8');
}

function ok(text, structuredContent) {
  return {
    content: [{ type: 'text', text }],
    structuredContent,
  };
}

function fail(message) {
  return {
    isError: true,
    content: [{ type: 'text', text: message }],
    structuredContent: { ok: false, error: message },
  };
}

const server = new McpServer({
  name: 'codex-console',
  version: '1.0.0',
});

// Small JSON text-only responses; full legacy structured UI contracts unchanged.
const selector = {threadId:z.string().min(4).max(256).optional(),taskId:z.string().min(1).max(80).optional()};
function compactTool(name,description,inputSchema,handler,budget=1500) {
  server.registerTool(name,{description,inputSchema,_meta:MODEL_META},async args=>{
    try { return compactReply(await handler(args),budget); } catch { return compactError(); }
  });
}
compactTool('task_status','Read compact task status (exactly one threadId or taskId). No history.',selector,
  args=>compactStatus(store,args),600);
compactTool('task_result','Read bounded worker-claimed result; not independent verification.',selector,
  args=>compactStatus(store,args,true));
compactTool('task_delta','Read changed compact result using revision from previous response.',{...selector,revision:z.string().regex(/^[a-f0-9]{64}$/).optional()},
  args=>compactDelta(store,args));
compactTool('get_operation_status','Read operation state without prompt, output or raw errors.',{opId:z.string().min(3).max(128)},
  ({opId})=>compactOperation(consoleDb.getOp(opId)),600);
compactTool('task_logs','Explicit cursor page of history event metadata; full log text remains in UI.',{threadId:z.string().min(4).max(256),cursor:z.number().int().min(0).max(Number.MAX_SAFE_INTEGER).optional(),limit:z.number().int().min(1).max(20).optional()},
  ({threadId,cursor=0,limit=10})=>store.getLogPage(threadId,cursor,limit),2500);
compactTool('task_list','List up to ten recent task IDs and states, without history.',{limit:z.number().int().min(1).max(10).optional()},
  ({limit=5})=>{
    const snap=store.getSnapshot({limit,includeManagedAgents:false});
    if(!snap.connected) throw new Error('State database unavailable');
    return {tasks:snap.tasks.map(t=>({threadId:t.id,status:t.status?.code})),scope:'recent'};
  },4000);

// UI Resource
server.registerResource(
  'codex-console-app',
  APP_URI,
  {
    title: 'Codex Console',
    description: 'Antigravity 侧栏可视化 Codex 任务控制台',
    mimeType: APP_MIME,
    _meta: { ui: { prefersBorder: false } },
  },
  async () => ({
    contents: [
      {
        uri: APP_URI,
        mimeType: APP_MIME,
        text: readAppHtml(),
        _meta: { ui: { prefersBorder: false } },
      },
    ],
  })
);

// 1. Entrypoint tool (opens side pane / global view)
server.registerTool(
  'open_codex_console',
  {
    title: 'Codex Console',
    description:
      '打开 Antigravity 侧栏 Codex 可视化控制台，查看本地 Codex CLI / Desktop / Worktree 任务、Goal 状态、受管子代理与跨会话 Change 绑定，并支持只读诊断与排队唤醒。',
    inputSchema: {
      tab: z.enum(['tasks', 'subagents', 'collab']).optional().describe('初始激活页签'),
      threadId: z.string().optional().describe('默认聚焦的 Codex 会话 ID'),
      query: z.string().optional().describe('初始搜索关键字'),
    },
    _meta: PANE_META,
  },
  async (args = {}) => {
    const snap = store.getSnapshot({ limit: 80 });
    const summaryText =
      `Codex Console 已连接（总会话 ${snap.stats.totalThreads}，已加载 ${snap.stats.loadedThreads}，` +
      `CLI Exec ${snap.stats.execCount}，运行中 ${snap.stats.runningCount}，` +
      `Goal 阻塞 ${snap.stats.goalBlockedCount}，受管子代理 ${snap.stats.managedCount}，` +
      `跨会话绑定 ${snap.stats.collabCount}）。`;

    return ok(summaryText, {
      initialTab: args.tab || 'tasks',
      initialThreadId: args.threadId || null,
      initialQuery: args.query || '',
      connected: snap.connected,
      stats: snap.stats,
      runtime: runner.getRuntimeInfo(),
    });
  }
);

// 2. Model + App: list tasks
server.registerTool(
  'list_codex_tasks',
  {
    title: '列出 Codex 任务',
    description: '查询本地 Codex CLI/Desktop/Worktree 会话、Goal 阻塞状态与受管子代理清单。',
    inputSchema: {
      query: z.string().optional().describe('按任务名、项目、分支或路径搜索'),
      project: z.string().optional().describe('按项目名过滤'),
      status: z.string().optional().describe('状态过滤：running/blocked/goal_active/exec_done/failed/archived'),
      onlyExec: z.boolean().optional().describe('仅看 CLI Exec / Worktree 派发任务'),
      includeSubagents: z.boolean().optional().describe('是否包含子代理线程'),
      limit: z.number().int().min(1).max(200).optional().describe('返回条数上限，默认 40'),
    },
    _meta: LEGACY_DETAIL_META,
  },
  async (args = {}) => {
    const snap = store.getSnapshot({ limit: Math.max(120, args.limit || 40) });
    let list = snap.tasks;
    if (!args.includeSubagents) {
      list = list.filter((t) => !t.isSubagent);
    }
    if (args.onlyExec) {
      list = list.filter((t) => t.isExec);
    }
    if (args.project) {
      list = list.filter((t) => t.projectName === args.project);
    }
    if (args.status) {
      list = list.filter((t) => t.status.code === args.status);
    }
    if (args.query) {
      const q = args.query.toLowerCase();
      list = list.filter((t) =>
        `${t.title} ${t.projectName} ${t.branch} ${t.cwd} ${t.goal?.objective || ''} ${t.id}`
          .toLowerCase()
          .includes(q)
      );
    }
    const sliced = list.slice(0, args.limit || 40);
    const lines = sliced.map(
      (t) =>
        `- [${t.status.label}] ${t.title} (${t.shortId}) | 项目:${t.projectName} | 分支:${t.branch || '-'} | 模型:${t.model || '-'} | tokens:${t.tokensUsed}`
    );
    return ok(
      `共匹配 ${list.length} 条 Codex 任务（展示前 ${sliced.length} 条）：\n${lines.join('\n')}`,
      { stats: snap.stats, totalMatched: list.length, tasks: sliced }
    );
  }
);

// 3. Model + App: get task detail
server.registerTool(
  'get_codex_task_detail',
  {
    title: '获取 Codex 任务详情',
    description: '获取指定 Codex 会话的 Goal 状态、最近对话记录、排队消息、控制台诊断记录与跨会话绑定。',
    inputSchema: {
      threadId: z.string().min(4).describe('Codex 会话 UUID 或前 8 位短 ID'),
    },
    _meta: LEGACY_DETAIL_META,
  },
  async ({ threadId }) => {
    let detail;
    try { detail = store.getThreadDetail(threadId); } catch (err) { return fail(err.message); }
    if (!detail.task) {
      return fail(`未找到 Codex 会话: ${threadId}`);
    }
    const git = await runner.inspectGit(detail.task.cwd);
    const summary =
      `会话 ${detail.task.title} (${detail.task.shortId})\n` +
      `状态: ${detail.task.status.label} | 项目: ${detail.task.projectName} | 目录: ${detail.task.cwd}\n` +
      `分支: ${detail.task.branch || '-'} | 模型: ${detail.task.model || '-'} | Tokens: ${detail.task.tokensUsed}\n` +
      `最近消息数: ${detail.messages.length} | 控制台操作数: ${detail.ops.length} | 绑定数: ${detail.bindings.length}`;
    return ok(summary, { ...detail, git });
  }
);

// 4. Model + App: read-only ask / diagnose blocker
server.registerTool(
  'ask_codex_readonly',
  {
    title: '只读提问 / 一键诊断卡点',
    description:
      '基于 codex exec fork --ephemeral（严格只读沙箱）对目标 Codex 会话执行非侵入式提问或一键诊断卡点，不污染原对话上下文且不修改工作区文件。',
    inputSchema: {
      threadId: z.string().min(4).describe('目标 Codex 会话 UUID'),
      prompt: z.string().optional().describe('自定义只读提问内容；留空则使用默认卡点诊断模板'),
      preset: z.enum(['diagnose_blocker', 'custom']).optional().describe('diagnose_blocker 为一键诊断卡点'),
    },
    _meta: BOTH_META,
  },
  async ({ threadId, prompt, preset }) => {
    let match;
    try { match = store.getThread(threadId); } catch (err) { return fail(err.message); }
    if (!match) return fail(`未找到目标 Codex 会话: ${threadId}`);

    const isDiagnose = preset === 'diagnose_blocker' || !prompt?.trim();
    const op = runner.startReadonlyAsk({
      threadId: match.id,
      prompt: isDiagnose ? DIAGNOSE_BLOCKER_PROMPT : prompt,
      cwd: match.cwd,
      opType: isDiagnose ? 'diagnose_blocker' : 'readonly_ask',
    });

    return ok(
      `已启动只读${isDiagnose ? '卡点诊断' : '提问'}（操作ID: ${op.id}，目标会话: ${match.title} [${match.shortId}]）。请稍后在控制台或通过 get_operation_status 查看结果。`,
      { op }
    );
  }
);

// 5. Model + App: send message (queue / resume / dispatch_resume / readonly)
server.registerTool(
  'send_codex_message',
  {
    title: '向 Codex 会话发送消息',
    description: '向指定 Codex 会话投递指令，支持排队唤醒（codex queue --resume）、同步续跑（codex exec resume）、dispatch.py 续跑或只读提问。',
    inputSchema: {
      threadId: z.string().min(4).describe('目标 Codex 会话 UUID'),
      message: z.string().min(1).describe('要发送的消息或执行指令'),
      mode: z.enum(['queue', 'resume', 'dispatch_resume', 'readonly']).optional().describe('默认 dispatch_resume；queue/resume 无受管授权时拒绝'),
      allowDuplicate: z.boolean().optional().describe('旧协议短时重复开关；不能绕过 requestId'),
      requestId: z.string().min(1).max(80).optional().describe('显式持久请求 ID，message 必须为 v2 JSON envelope'),
      retryOf: z.string().min(1).max(80).optional().describe('明确引用失败请求，不代表授权'),
    },
    _meta: BOTH_META,
  },
  async ({ threadId, message, mode = 'dispatch_resume', allowDuplicate = false, requestId, retryOf }) => {
    let match;
    try { match = store.getThread(threadId); } catch (err) { return fail(err.message); }
    if (!match) return fail(`未找到目标 Codex 会话: ${threadId}`);

    try {
      const op = await runner.sendMessage({
        threadId: match.id,
        message,
        mode,
        cwd: match.cwd,
        allowDuplicate,
        taskId: match.dispatchTask?.taskId || null,
        requestId, retryOf,
      });
      return ok(
        `消息操作已提交（模式: ${mode}，状态: ${op.status}，操作ID: ${op.id}）${op.errorText ? `\n说明: ${op.errorText}` : ''}`,
        { op }
      );
    } catch (err) {
      return fail(err.message || String(err));
    }
  }
);

// 6. Model + App: spawn managed worker via dispatch.py
server.registerTool(
  'spawn_codex_worker',
  {
    title: '新建受管 Codex 子代理',
    description: '通过 multi-agent-dispatch (dispatch.py run) 在隔离 Git Worktree 中启动新的 Codex 子代理任务，并可选写入跨会话 Change 绑定。',
    inputSchema: {
      cwd: z.string().min(1).describe('目标仓库或工作目录绝对路径'),
      prompt: z.string().min(1).describe('给 Codex 子代理的清晰任务指令'),
      taskId: z.string().optional().describe('可选自定义 task_id；requestId 时必填'),
      requestId: z.string().min(1).max(80).optional().describe('显式持久请求 ID，prompt 必须为 v2 JSON envelope'),
      difficulty: z.enum(['auto', 'low', 'medium', 'hard', 'extreme']).optional(),
      quality: z.enum(['smart', 'max', 'balanced']).optional(),
      isolation: z.enum(['worktree', 'inplace', 'auto']).optional(),
      network: z.boolean().optional().describe('当前版本无可信宿主授权；true 会被执行层拒绝'),
      changeKey: z.string().optional().describe('可选 OpenSpec Change / Goal 标识，用于跨会话绑定'),
      goalTitle: z.string().optional().describe('可选 Goal 标题'),
    },
    _meta: BOTH_META,
  },
  async (args) => {
    try {
      const op = runner.spawnWorker(args);
      return ok(
        `已启动受管 Codex 子代理任务（操作ID: ${op.id}，目录: ${args.cwd}，策略: ${args.quality || 'smart'}/${args.difficulty || 'auto'}/${args.isolation || 'worktree'}${args.network ? '/network' : ''}）。`,
        { op }
      );
    } catch (err) {
      return fail(err.message || String(err));
    }
  }
);

// 7. Model + App: SQLite cross-session collaboration bindings
server.registerTool(
  'manage_collab_binding',
  {
    title: '管理跨会话 Change ↔ Codex 绑定',
    description:
      '维护 SQLite 跨会话协作中间件：记录 OpenSpec Change / BLACKBOARD 任务与 Codex 会话 ID 的绑定关系、责任边界（antigravity vs codex）与交接日志。',
    inputSchema: {
      action: z.enum(['list', 'upsert', 'delete', 'log_message']),
      id: z.string().optional().describe('绑定记录 ID（删除/更新/写日志时使用）'),
      changeKey: z.string().optional().describe('Change / 任务标识，如 feat-codex-console'),
      goalTitle: z.string().optional().describe('目标描述'),
      threadId: z.string().optional().describe('绑定的 Codex thread_id'),
      taskId: z.string().optional().describe('绑定的 dispatch task_id'),
      ownerRole: z.enum(['codex', 'antigravity', 'shared']).optional().describe('责任归属'),
      status: z.enum(['active', 'blocked', 'reviewing', 'completed', 'archived']).optional(),
      repoPath: z.string().optional(),
      branch: z.string().optional(),
      notes: z.string().optional(),
      messageContent: z.string().optional().describe('action=log_message 时的交接记录正文'),
      author: z.string().optional(),
    },
    _meta: BOTH_META,
  },
  async (args) => {
    try {
      if (args.action === 'list') {
        const bindings = consoleDb.listBindings({ threadId: args.threadId || null });
        return ok(`当前共有 ${bindings.length} 条跨会话协作绑定。`, { bindings });
      }
      if (args.action === 'upsert') {
        if (!args.changeKey?.trim()) return fail('upsert 需要提供 changeKey');
        const binding = consoleDb.upsertBinding({
          id: args.id || null,
          changeKey: args.changeKey.trim(),
          goalTitle: args.goalTitle || args.changeKey.trim(),
          threadId: args.threadId || null,
          taskId: args.taskId || null,
          ownerRole: args.ownerRole || 'codex',
          status: args.status || 'active',
          repoPath: args.repoPath || null,
          branch: args.branch || null,
          notes: args.notes || '',
        });
        return ok(`已保存跨会话绑定：${binding.changeKey} -> ${binding.threadId || '未绑定会话'}`, { binding });
      }
      if (args.action === 'delete') {
        if (!args.id) return fail('delete 需要提供绑定 id');
        const res = consoleDb.deleteBinding(args.id);
        return ok(`已删除绑定 ${args.id}`, res);
      }
      if (args.action === 'log_message') {
        if (!args.messageContent?.trim()) return fail('log_message 需要提供 messageContent');
        const msg = consoleDb.addCollabMessage({
          bindingId: args.id || null,
          threadId: args.threadId || null,
          direction: 'handoff',
          author: args.author || 'antigravity',
          content: args.messageContent.trim(),
        });
        return ok(`已记录跨会话协作日志 (${msg.id})`, { message: msg });
      }
      return fail(`不支持的操作: ${args.action}`);
    } catch (err) {
      return fail(err.message || String(err));
    }
  }
);

// 8. App-only tools (high-frequency UI polling & local state mutations)
server.registerTool(
  'console_snapshot',
  {
    title: 'Console Snapshot',
    description: '获取控制台完整实时快照（仅前端 App 可调用）',
    inputSchema: {
      limit: z.number().int().min(10).max(250).optional(),
    },
    _meta: APP_ONLY_META,
  },
  async ({ limit = 160 } = {}) => {
    const snap = store.getSnapshot({ limit });
    const quota = quotaTracker.getFastQuota();
    return ok('snapshot ok', {
      ...snap,
      quota,
      runtime: runner.getRuntimeInfo(),
    });
  }
);

server.registerTool(
  'console_refresh_quota',
  {
    title: 'Refresh Codex Quota Live',
    description: '通过官方 codex app-server 实时查询 5 小时/周额度与重置时间（仅前端 App 可调用）',
    inputSchema: {},
    _meta: APP_ONLY_META,
  },
  async () => {
    const quota = await quotaTracker.refreshLive();
    return ok('quota refreshed', { quota });
  }
);

server.registerTool(
  'console_toggle_pin',
  {
    title: 'Toggle Pin / Hide / Rename Thread',
    description: '置顶、软隐藏或设置任务别名（保存在控制台自有 SQLite，不修改 Codex 原库）',
    inputSchema: {
      threadId: z.string().min(4),
      pinned: z.boolean().optional(),
      hidden: z.boolean().optional(),
      customTitle: z.string().optional(),
    },
    _meta: APP_ONLY_META,
  },
  async ({ threadId, pinned, hidden, customTitle }) => {
    const pref = consoleDb.setThreadPref(threadId, { pinned, hidden, customTitle });
    return ok('updated pref', { pref });
  }
);

server.registerTool(
  'console_get_op',
  {
    title: 'Get Background Operation',
    description: '轮询后台操作状态与结果',
    inputSchema: {
      opId: z.string().min(3),
    },
    _meta: APP_ONLY_META,
  },
  async ({ opId }) => {
    const op = consoleDb.getOp(opId);
    if (!op) return fail(`未找到操作: ${opId}`);
    return ok(`op ${op.status}`, { op });
  }
);

server.registerTool(
  'console_git_inspect',
  {
    title: 'Inspect Git & Worktree',
    description: '只读检查会话目录的 Git 分支、变更文件与 docs/BLACKBOARD.md',
    inputSchema: {
      cwd: z.string().min(1),
    },
    _meta: APP_ONLY_META,
  },
  async ({ cwd }) => {
    const git = await runner.inspectGit(cwd);
    return ok('git inspect ok', { git });
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error('[codex-console] fatal error:', err);
  process.exit(1);
});
