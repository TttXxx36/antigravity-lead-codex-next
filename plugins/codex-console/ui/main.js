import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
} from '@modelcontextprotocol/ext-apps';
import { z } from 'zod';
import { renderPixelCat } from './cat-pet.js';

const app = new App({ name: 'Codex Console', version: '1.2.0' }, {});
const SLEEP_IDLE_MS = 12 * 60 * 1000; // 12 min idle -> zZz sleeping (within 10-15 min)

const MODE_TIPS = {
  queue: '排队唤醒：通过 codex queue 入队并唤醒会话；若 CLI 已退出可切「同步续跑」',
  resume: '同步续跑：通过 codex exec resume 继续当前会话并在后台返回结果',
  dispatch_resume: 'Dispatch 续跑：通过 dispatch.py 在隔离 Worktree 中继续该受管子代理',
  readonly: '只读提问：通过 codex exec fork --ephemeral 只读查询，不改文件、不污染原上下文',
};

const ICON_HIDE = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="3" width="12" height="3" rx="1"/><path d="M3.5 6v6.5A1.5 1.5 0 0 0 5 14h6a1.5 1.5 0 0 0 1.5-1.5V6"/><path d="M6.5 9.5h3"/></svg>`;
const ICON_RESTORE = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8a5 5 0 1 1 1.5 3.6"/><path d="M3 4.5V8h3.5"/></svg>`;

const state = {
  connected: false,
  capabilities: {},
  stats: {
    loadedThreads: 0,
    visibleThreads: 0,
    agyCount: 0,
    runningCount: 0,
    goalBlockedCount: 0,
    managedCount: 0,
    collabCount: 0,
    runningOpsCount: 0,
  },
  tasks: [],
  managedAgents: [],
  bindings: [],
  quota: null,
  refreshingQuota: false,

  activeTab: 'tasks',          // tasks | subagents | collab
  detailSubTab: 'history',     // history | ops | git
  historyNewestFirst: true,
  showDesktopTasks: false,
  showHiddenDrawer: false,

  selectedThreadId: null,
  selectedAgentId: null,
  selectedBindingId: null,
  selectedDetail: null,
  selectedGit: null,

  loadingSnapshot: false,
  sendingMessage: false,
  searchQuery: '',
  composerText: '',
  composerMode: 'queue',
  allowDuplicate: false,

  catMeowing: false,
  catMeowTimer: null,
  catFreezeLeft: null,
  catFreezeFlip: 1,
  lastCatWakeMs: 0,

  modal: null,                 // null | spawn | readonly | binding | rename
  toast: null,
  toastTimer: null,
  autoRefreshTimer: null,
  lastPollMs: 12_000,
};

// ---------------- Formatters ----------------

function esc(v) {
  return String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function relTime(ms) {
  if (!ms) return '';
  const sec = Math.max(0, Math.floor((Date.now() - Number(ms)) / 1000));
  if (sec < 60) return '刚刚';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h`;
  return `${Math.floor(hr / 24)}d`;
}

function clockTime(ms) {
  if (!ms) return '';
  return new Date(Number(ms)).toTimeString().slice(0, 5);
}

function fmtTokens(n) {
  const num = Number(n || 0);
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M tok`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}k tok`;
  return num > 0 ? `${num} tok` : '';
}

function fmtDuration(sec) {
  const s = Number(sec || 0);
  if (s <= 0) return '';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

function dotClass(code) {
  if (code === 'running' || code === 'goal_active') return 'running';
  if (code === 'blocked' || code === 'limited') return 'blocked';
  if (code === 'failed') return 'failed';
  if (code === 'exec_done' || code === 'complete' || code === 'completed') return 'done';
  return '';
}

function quotaTone(rem) {
  if (typeof rem !== 'number') return 'muted';
  if (rem <= 20) return 'danger';
  if (rem <= 50) return 'warn';
  return 'healthy';
}

function fmtReset(ms) {
  if (!ms) return '';
  const diff = Math.floor((Number(ms) - Date.now()) / 1000);
  const d = new Date(Number(ms));
  const clk = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  if (diff <= 0) return clk;
  const days = Math.floor(diff / 86400);
  const hrs = Math.floor((diff % 86400) / 3600);
  const mins = Math.floor((diff % 3600) / 60);
  if (days > 0) return `${days}d ${hrs}h · ${clk}`;
  if (hrs > 0) return `${hrs}h ${mins}m · ${clk}`;
  return `${Math.max(1, mins)}m · ${clk}`;
}

function renderMd(text) {
  if (!text) return '';
  const lines = String(text).split('\n');
  let html = '';
  let inList = false;
  let inCode = false;
  let codeBuf = [];
  const flush = () => {
    if (inList) {
      html += '</ul>';
      inList = false;
    }
  };
  const inline = (s) =>
    esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      flush();
      if (!inCode) {
        inCode = true;
        codeBuf = [];
      } else {
        inCode = false;
        html += `<pre>${esc(codeBuf.join('\n'))}</pre>`;
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(line);
      continue;
    }
    const t = line.trim();
    if (!t) {
      flush();
      continue;
    }
    const lm = t.match(/^[-*•]\s+(.*)$/) || t.match(/^\d+[.)]\s+(.*)$/);
    if (lm) {
      if (!inList) {
        html += '<ul>';
        inList = true;
      }
      html += `<li>${inline(lm[1])}</li>`;
      continue;
    }
    flush();
    if (t.startsWith('### ')) html += `<p><strong>${inline(t.slice(4))}</strong></p>`;
    else if (t.startsWith('## ')) html += `<p><strong>${inline(t.slice(3))}</strong></p>`;
    else html += `<p>${inline(t)}</p>`;
  }
  flush();
  if (inCode && codeBuf.length) html += `<pre>${esc(codeBuf.join('\n'))}</pre>`;
  return html;
}

function oneLineClean(text) {
  return String(text || '')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function showToast(text, kind = 'ok') {
  state.toast = { text, kind };
  if (state.toastTimer) clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    state.toast = null;
    render();
  }, 2600);
  render();
}

// ---------------- Server RPC ----------------

async function callTool(name, args = {}) {
  const res = await app.callServerTool({ name, arguments: args });
  if (res?.isError) {
    throw new Error(res?.structuredContent?.error || res?.content?.[0]?.text || name);
  }
  return res?.structuredContent ?? {};
}

async function refreshSnapshot({ silent = false } = {}) {
  if (state.loadingSnapshot) return;
  state.loadingSnapshot = true;
  if (!silent) render();
  try {
    const data = await callTool('console_snapshot', { limit: 180 });
    state.connected = Boolean(data.connected);
    state.stats = data.stats || state.stats;
    state.tasks = data.tasks || [];
    state.managedAgents = data.managedAgents || [];
    state.bindings = data.bindings || [];
    if (data.quota) state.quota = data.quota;

    if (!state.selectedThreadId && state.tasks.length) {
      const visible = state.tasks.filter((t) => !t.isSubagent && !t.hidden);
      const pick =
        visible.find((t) => t.isAgyDispatched && t.status.code === 'running') ||
        visible.find((t) => t.pinned) ||
        visible.find((t) => t.isAgyDispatched) ||
        visible[0] ||
        state.tasks[0];
      state.selectedThreadId = pick?.id || null;
    }
    if (!state.selectedAgentId && state.managedAgents.length) {
      state.selectedAgentId = state.managedAgents[0].id;
    }
    if (!state.selectedBindingId && state.bindings.length) {
      state.selectedBindingId = state.bindings[0].id;
    }
    if (state.selectedThreadId) {
      await loadThreadDetail(state.selectedThreadId, { silent: true });
    }
    scheduleAutoRefresh();
  } catch (err) {
    if (!silent) showToast(err.message, 'error');
  } finally {
    state.loadingSnapshot = false;
    render();
  }
}

async function refreshQuotaLive({ silent = false } = {}) {
  if (state.refreshingQuota) return;
  state.refreshingQuota = true;
  if (!silent) render();
  try {
    const res = await callTool('console_refresh_quota', {});
    if (res?.quota) state.quota = res.quota;
    if (!silent && state.quota?.available) {
      showToast(`额度已同步 · 剩余 ${Math.round(state.quota.bottleneck.remainingPercent)}%`);
    }
  } catch (err) {
    if (!silent) showToast(err.message, 'error');
  } finally {
    state.refreshingQuota = false;
    render();
  }
}

async function loadThreadDetail(threadId, { silent = false } = {}) {
  if (!threadId) return;
  state.selectedThreadId = threadId;
  try {
    const detail = await callTool('get_codex_task_detail', { threadId });
    state.selectedDetail = detail;
    state.selectedGit = detail.git || null;
  } catch (err) {
    if (!silent) showToast(err.message, 'error');
  } finally {
    render();
  }
}

async function updateThreadPref(threadId, patch, toastMsg = '') {
  try {
    await callTool('console_toggle_pin', { threadId, ...patch });
    if (patch.hidden === true && state.selectedThreadId === threadId) {
      const next = state.tasks.find((t) => !t.isSubagent && !t.hidden && t.id !== threadId);
      if (next) state.selectedThreadId = next.id;
    }
    await refreshSnapshot({ silent: true });
    if (toastMsg) showToast(toastMsg);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function triggerReadonly(threadId, prompt = '', preset = 'diagnose_blocker') {
  try {
    const res = await callTool('ask_codex_readonly', { threadId, prompt, preset });
    state.detailSubTab = 'ops';
    showToast(preset === 'diagnose_blocker' ? '已发起只读诊断' : '已发起只读提问');
    await loadThreadDetail(threadId, { silent: true });
    if (res?.op?.id) pollOp(res.op.id, threadId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function pollOp(opId, threadId) {
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 2500));
    try {
      const { op } = await callTool('console_get_op', { opId });
      if (!op || op.status !== 'running') {
        await refreshSnapshot({ silent: true });
        if (threadId && state.selectedThreadId === threadId) {
          await loadThreadDetail(threadId, { silent: true });
        }
        return;
      }
    } catch {
      return;
    }
  }
}

async function sendComposer() {
  const task = selectedTask();
  const msg = state.composerText.trim();
  if (!task || !msg || state.sendingMessage) return;
  state.sendingMessage = true;
  render();
  try {
    const res = await callTool('send_codex_message', {
      threadId: task.id,
      message: msg,
      mode: state.composerMode,
      allowDuplicate: state.allowDuplicate,
    });
    state.composerText = '';
    if (state.composerMode === 'readonly') state.detailSubTab = 'ops';
    const op = res?.op;
    if (op?.status === 'failed') showToast(op.errorText || '发送失败', 'error');
    else if (op?.status === 'running') {
      showToast('已发送，后台执行中');
      pollOp(op.id, task.id);
    } else showToast('已发送给 Codex');
    await loadThreadDetail(task.id, { silent: true });
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    state.sendingMessage = false;
    render();
  }
}

async function sendBack(text) {
  if (!state.capabilities?.message) return;
  try {
    await app.sendMessage({ role: 'user', content: [{ type: 'text', text }] });
    showToast('已发回当前对话');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openFile(absPath) {
  if (!absPath) return;
  const uri = absPath.startsWith('file://') ? absPath : `file://${encodeURI(absPath)}`;
  try {
    await app.request(
      { method: 'com.google.antigravity/toggle-aux-pane', params: { tabType: 'fileView', uri } },
      z.object({ isError: z.boolean().optional() }).passthrough()
    );
  } catch {
    showToast('无法在当前视图打开文件', 'error');
  }
}

function copyText(str) {
  navigator.clipboard?.writeText(str).then(() => showToast('已复制'), () => showToast(str));
}

// ---------------- Selectors ----------------

function selectedTask() {
  return state.selectedDetail?.task || state.tasks.find((t) => t.id === state.selectedThreadId) || null;
}

function selectedAgent() {
  return state.managedAgents.find((a) => a.id === state.selectedAgentId) || state.managedAgents[0] || null;
}

function selectedBinding() {
  return state.bindings.find((b) => b.id === state.selectedBindingId) || state.bindings[0] || null;
}

function sortPriority(a, b) {
  const rank = (t) =>
    t.status.code === 'running' ? 0 : t.status.code === 'blocked' ? 1 : t.isManagedDispatch ? 2 : 3;
  const d = rank(a) - rank(b);
  return d !== 0 ? d : (b.updatedAtMs || 0) - (a.updatedAtMs || 0);
}

function filteredTasks() {
  const q = state.searchQuery.trim().toLowerCase();
  return state.tasks.filter((t) => {
    if (t.isSubagent) return false;
    if (!q) return true;
    return `${t.title} ${t.projectName} ${t.branch} ${t.cwd} ${t.id} ${t.changeKeys.join(' ')}`
      .toLowerCase()
      .includes(q);
  });
}

function getCatState() {
  const running = state.stats.runningCount + state.stats.runningOpsCount;
  const blocked = state.stats.goalBlockedCount;
  if (running > 0) {
    return { mode: 'working', label: `工作中（${running} 个进行中）· 点击喵一声并定位` };
  }
  if (blocked > 0) {
    return { mode: 'blocked', label: `有 ${blocked} 个任务阻塞 · 点击喵一声并查看` };
  }

  // Determine recent activity within 12 minutes -> strolling; >= 12 min idle -> zZz sleeping
  const agyTasks = state.tasks.filter((t) => !t.isSubagent && t.isAgyDispatched);
  const latestTaskMs = agyTasks.reduce((m, t) => Math.max(m, Number(t.updatedAtMs || 0)), 0);
  const latestActivity = Math.max(latestTaskMs, state.lastCatWakeMs);
  const idleMs = latestActivity ? Date.now() - latestActivity : SLEEP_IDLE_MS + 1;

  if (idleMs < SLEEP_IDLE_MS) {
    const leftMin = Math.max(1, Math.ceil((SLEEP_IDLE_MS - idleMs) / 60_000));
    return { mode: 'strolling', label: `散步中（约 ${leftMin} 分钟无任务后休眠）· 点击喵一声` };
  }
  return { mode: 'sleeping', label: '已休眠 ZZZ · 点击叫醒喵一声' };
}

// ---------------- Topbar Widgets ----------------

function renderQuotaWidget() {
  const q = state.quota;
  const r = 6.2;
  const circ = 2 * Math.PI * r;
  const has = Boolean(q?.available && q?.bottleneck);
  const rem = has ? Math.round(q.bottleneck.remainingPercent) : null;
  const tone = quotaTone(rem);
  const offset = has ? circ * (1 - Math.max(0, Math.min(100, q.bottleneck.remainingPercent)) / 100) : circ;
  const plan = q?.planType ? String(q.planType).toUpperCase() : 'CODEX';

  const rows = has
    ? q.windows
        .map(
          (w) => `
          <div class="quota-row">
            <div class="quota-row-top">
              <span>${esc(w.label)}</span>
              <strong>剩余 ${Math.round(w.remainingPercent)}%</strong>
            </div>
            <div class="quota-bar-track">
              <div class="quota-bar-fill ${quotaTone(w.remainingPercent)}" style="width:${Math.max(0, Math.min(100, w.remainingPercent))}%"></div>
            </div>
            <div class="quota-row-sub">
              <span>已用 ${w.usedPercent}%</span>
              <span>${esc(fmtReset(w.resetsAtMs))}</span>
            </div>
          </div>`
        )
        .join('')
    : `<div style="font-size:12px;color:var(--text-2)">暂未读取到 Codex 额度</div>`;

  return `
    <div class="quota-wrap">
      <button class="quota-btn" id="btnQuotaRing" aria-label="Codex 剩余额度">
        <svg class="quota-ring" viewBox="0 0 16 16" aria-hidden="true">
          <circle class="quota-track" cx="8" cy="8" r="${r}"></circle>
          <circle class="quota-arc ${tone}" cx="8" cy="8" r="${r}" stroke-dasharray="${circ.toFixed(2)}" stroke-dashoffset="${offset.toFixed(2)}"></circle>
        </svg>
        <span>${state.refreshingQuota ? '…' : has ? `${rem}%` : '--'}</span>
      </button>
      <div class="quota-popover" role="tooltip">
        <div class="quota-pop-head">
          <span class="quota-pop-title">Codex 剩余额度 <span class="plan-tag">${esc(plan)}</span></span>
          <button class="text-btn violet" id="btnQuotaRefresh">${state.refreshingQuota ? '同步中' : '实时同步'}</button>
        </div>
        <div class="quota-pop-desc">圆环优先显示 5 小时与周额度中的剩余最小值，点击圆环立即刷新</div>
        ${rows}
        <div class="quota-pop-foot">
          ${q?.resetCreditsAvailable > 0 ? `<span>免费额度重置券：${q.resetCreditsAvailable} 张可用</span>` : ''}
          ${q?.credits?.hasCredits ? `<span>额外 Credits：${q.credits.unlimited ? '无限' : esc(q.credits.balance)}</span>` : ''}
          <span>来源：${q?.source === 'live' ? '官方实时' : '本地缓存'} · ${esc(relTime(q?.updatedAtMs))}</span>
        </div>
      </div>
    </div>
  `;
}

// ---------------- Unified Left Rail (Consistent Across All 3 Tabs!) ----------------

function renderTaskRow(t, inHiddenDrawer = false) {
  const sel = t.id === state.selectedThreadId;
  const snippet = t.latestReply || t.branch || t.projectName;
  const subMeta = [t.projectName, t.branch].filter(Boolean).join(' · ');
  return `
    <div class="task-row ${sel ? 'selected' : ''}" data-select-thread="${esc(t.id)}">
      <div class="task-row-top">
        <span class="status-dot ${dotClass(t.status.code)}"></span>
        <span class="task-row-title" title="${esc(t.title)}">${esc(t.title)}</span>
        <span class="task-row-time">${esc(relTime(t.updatedAtMs))}</span>
      </div>
      ${subMeta ? `<div class="task-row-meta">${esc(subMeta)}</div>` : ''}
      <div class="task-row-sub">
        <span class="task-row-snippet ${t.status.code === 'blocked' ? 'warn' : ''}">${esc(snippet)}</span>
        <span class="row-actions">
          ${!inHiddenDrawer ? `
            <button
              class="row-micro-btn ${t.pinned ? 'pinned' : ''} tip-trigger tip-top-right"
              data-pin-thread="${esc(t.id)}"
              data-pinned="${t.pinned ? '1' : '0'}"
              data-tip="${t.pinned ? '取消置顶' : '置顶到顶部'}"
            >${t.pinned ? '★' : '☆'}</button>
          ` : ''}
          <button
            class="row-micro-btn tip-trigger tip-top-right"
            data-hide-thread="${esc(t.id)}"
            data-hidden="${inHiddenDrawer ? '1' : '0'}"
            data-tip="${inHiddenDrawer ? '移出隐藏抽屉' : '隐藏到下方抽屉（不归档原会话）'}"
          >${inHiddenDrawer ? ICON_RESTORE : ICON_HIDE}</button>
        </span>
      </div>
    </div>
  `;
}

function renderTasksLeftRail() {
  const all = filteredTasks();
  const visible = all.filter((t) => !t.hidden);
  const hidden = all.filter((t) => t.hidden);

  const pinned = visible.filter((t) => t.pinned).sort(sortPriority);
  const unpinned = visible.filter((t) => !t.pinned);
  const agy = unpinned.filter((t) => t.isAgyDispatched).sort(sortPriority);
  const desktop = unpinned.filter((t) => !t.isAgyDispatched);
  const desktopOpen = state.showDesktopTasks || Boolean(state.searchQuery.trim()) || agy.length === 0;

  let itemsHtml = '';
  if (!visible.length && !hidden.length) {
    itemsHtml = `<div class="detail-empty">无匹配任务</div>`;
  } else {
    if (pinned.length) {
      itemsHtml += `<div class="list-group-label"><span>已置顶</span><span>${pinned.length}</span></div>`;
      itemsHtml += pinned.map((t) => renderTaskRow(t, false)).join('');
    }
    if (agy.length) {
      itemsHtml += `<div class="list-group-label"><span>Antigravity</span><span>${agy.length}</span></div>`;
      itemsHtml += agy.map((t) => renderTaskRow(t, false)).join('');
    }
    if (desktop.length) {
      itemsHtml += `<div class="list-group-label toggle tip-trigger tip-top" id="btnToggleDesktop" data-tip="展开或折叠 GPT 桌面端原有会话"><span>${desktopOpen ? '▾' : '▸'} GPT</span><span>${desktop.length}</span></div>`;
      if (desktopOpen) itemsHtml += desktop.map((t) => renderTaskRow(t, false)).join('');
    }
  }

  const hiddenDrawerHtml = hidden.length
    ? `
      <div class="hidden-drawer">
        <button class="hidden-drawer-toggle" id="btnToggleHidden">
          <span>${state.showHiddenDrawer ? '▾' : '▸'} 已隐藏</span>
          <span>${hidden.length}</span>
        </button>
        ${state.showHiddenDrawer ? `<div class="hidden-drawer-body">${hidden.map((t) => renderTaskRow(t, true)).join('')}</div>` : ''}
      </div>`
    : '';

  return `
    <aside class="left-rail">
      <div class="search-wrap">
        <input id="searchInput" class="search-input" type="text" placeholder="搜索任务、项目、分支…" value="${esc(state.searchQuery)}" />
      </div>
      <div class="task-list">${itemsHtml}</div>
      ${hiddenDrawerHtml}
    </aside>
  `;
}

function renderSubagentsLeftRail() {
  const q = state.searchQuery.trim().toLowerCase();
  const list = state.managedAgents.filter((a) =>
    !q ? true : `${a.title} ${a.taskId} ${a.branch} ${a.projectName} ${a.summary}`.toLowerCase().includes(q)
  );
  const cur = selectedAgent();

  const itemsHtml = !list.length
    ? `<div class="detail-empty">暂无受管子代理</div>`
    : `<div class="list-group-label"><span>受管 Worktree</span><span>${list.length}</span></div>` +
      list
        .map((a) => {
          const sel = cur && a.id === cur.id;
          return `
            <div class="task-row ${sel ? 'selected' : ''}" data-select-agent="${esc(a.id)}">
              <div class="task-row-top">
                <span class="status-dot ${dotClass(a.status)}"></span>
                <span class="task-row-title" title="${esc(a.title)}">${esc(a.title)}</span>
              </div>
              <div class="task-row-meta">${esc([a.branch, a.model].filter(Boolean).join(' · '))}</div>
              <div class="task-row-sub">
                <span class="task-row-snippet">${esc(a.summary || a.worktreePath)}</span>
              </div>
            </div>`;
        })
        .join('');

  return `
    <aside class="left-rail">
      <div class="rail-search-row">
        <input id="searchInput" class="search-input" type="text" placeholder="搜索子代理…" value="${esc(state.searchQuery)}" />
        <button class="icon-btn accent tip-trigger tip-bottom-right" id="btnSpawnFromTab" data-tip="新建受管 Codex 子代理">+</button>
      </div>
      <div class="task-list">${itemsHtml}</div>
    </aside>
  `;
}

function renderCollabLeftRail() {
  const q = state.searchQuery.trim().toLowerCase();
  const list = state.bindings.filter((b) =>
    !q ? true : `${b.changeKey} ${b.goalTitle} ${b.ownerRole} ${b.threadId || ''}`.toLowerCase().includes(q)
  );
  const cur = selectedBinding();

  const itemsHtml = !list.length
    ? `<div class="detail-empty">暂无跨会话绑定</div>`
    : `<div class="list-group-label"><span>Change 绑定</span><span>${list.length}</span></div>` +
      list
        .map((b) => {
          const sel = cur && b.id === cur.id;
          return `
            <div class="task-row ${sel ? 'selected' : ''}" data-select-binding="${esc(b.id)}">
              <div class="task-row-top">
                <span class="status-dot ${dotClass(b.status)}"></span>
                <span class="task-row-title" title="${esc(b.changeKey)}">${esc(b.changeKey)}</span>
                <span class="plan-tag">${esc(b.ownerRole)}</span>
              </div>
              <div class="task-row-sub">
                <span class="task-row-snippet">${esc(b.goalTitle)}</span>
              </div>
            </div>`;
        })
        .join('');

  return `
    <aside class="left-rail">
      <div class="rail-search-row">
        <input id="searchInput" class="search-input" type="text" placeholder="搜索协作绑定…" value="${esc(state.searchQuery)}" />
        <button class="icon-btn accent tip-trigger tip-bottom-right" id="btnNewBinding" data-tip="新建 Change ↔ Codex 跨会话绑定">+</button>
      </div>
      <div class="task-list">${itemsHtml}</div>
    </aside>
  `;
}

// ---------------- Right Detail Panes ----------------

function renderHistory(detail, task) {
  const msgs = detail?.messages || [];
  if (!msgs.length) return `<div class="detail-empty">暂无记录</div>`;
  const ordered = state.historyNewestFirst ? [...msgs].reverse() : msgs;
  const canSend = Boolean(state.capabilities?.message);

  return `<div class="feed-inner">${ordered
    .map((m, idx) => {
      const isLatest = state.historyNewestFirst ? idx === 0 : idx === ordered.length - 1;
      if (m.type === 'reasoning' || m.type === 'commandExecution' || m.type === 'fileChange') {
        const kind = m.type === 'reasoning' ? '思考' : m.type === 'commandExecution' ? '命令' : '文件';
        const firstLine = oneLineClean(m.text.split('\n')[0]).slice(0, 130);
        return `
          <details class="trace-row">
            <summary>
              <span class="trace-kind">${kind}</span>
              <span class="trace-line">${esc(firstLine)}</span>
              <span class="trace-time">${esc(clockTime(m.createdAtMs))}</span>
            </summary>
            <div class="trace-body">${esc(m.text)}</div>
          </details>`;
      }

      const isUser = m.type === 'userMessage';
      const role = isUser ? '主控' : m.type === 'plan' ? '计划' : 'Codex';
      return `
        <article class="msg-card ${isUser ? 'user' : ''} ${isLatest ? 'latest' : ''}">
          <div class="msg-head">
            <span class="msg-role">${isLatest ? '<span class="latest-dot"></span>' : ''}${role}</span>
            <div style="display:flex;align-items:center;gap:6px">
              <span>${esc(clockTime(m.createdAtMs))}</span>
              ${canSend && !isUser ? `<button class="text-btn violet" data-send-back="${esc(`【${task.title} (${task.shortId})】\n${m.text}`)}">发回对话</button>` : ''}
            </div>
          </div>
          <div class="msg-body">${isUser ? esc(m.text) : renderMd(m.text)}</div>
        </article>`;
    })
    .join('')}</div>`;
}

function renderOps(detail, task) {
  const ops = detail?.ops || [];
  const canSend = Boolean(state.capabilities?.message);
  if (!ops.length) {
    return `<div class="detail-empty"><button class="text-btn violet" id="btnEmptyDiagnose">发起只读卡点诊断</button></div>`;
  }
  const names = {
    diagnose_blocker: '卡点诊断',
    readonly_ask: '只读提问',
    queue_send: '排队唤醒',
    exec_resume: '同步续跑',
    dispatch_resume: 'Dispatch 续跑',
    spawn_worker: '新建子代理',
  };
  return `<div class="feed-inner">${ops
    .map((op) => {
      const chatText = `【${task.title} (${task.shortId}) · ${names[op.opType] || op.opType}】\n${op.outputText || op.errorText || op.status}`;
      return `
        <article class="op-card ${esc(op.status)}">
          <div class="msg-head">
            <span class="msg-role">${esc(names[op.opType] || op.opType)} · ${esc(op.status.toUpperCase())}</span>
            <div style="display:flex;align-items:center;gap:6px">
              <span>${esc(clockTime(op.startedAt))}</span>
              ${canSend && op.status !== 'running' ? `<button class="text-btn violet" data-send-back="${esc(chatText)}">发回对话</button>` : ''}
            </div>
          </div>
          <div class="op-prompt">${esc(op.prompt)}</div>
          ${op.outputText ? `<div class="msg-body">${renderMd(op.outputText)}</div>` : ''}
          ${op.errorText ? `<div class="op-err">${esc(op.errorText)}</div>` : ''}
        </article>`;
    })
    .join('')}</div>`;
}

function renderGit(git) {
  if (!git) return `<div class="detail-empty">读取中…</div>`;
  if (!git.isGit) return `<div class="detail-empty">${esc(git.error || '非 Git 目录')}</div>`;
  if (!git.files?.length) return `<div class="detail-empty">工作区干净</div>`;
  return `<div class="feed-inner">${git.files
    .map(
      (f) => `
      <div class="git-row">
        <span><span class="git-xy">${esc(f.xy)}</span>${esc(f.file)}</span>
        <button class="text-btn violet" data-open-file="${esc(f.absPath)}">打开</button>
      </div>`
    )
    .join('')}</div>`;
}

function renderTaskDetailPane() {
  const task = selectedTask();
  if (!task) return `<main class="detail-pane"><div class="detail-empty">选择一个任务</div></main>`;
  const detail = state.selectedDetail;
  const git = state.selectedGit;
  const metaParts = [
    task.projectName,
    task.branch,
    task.model,
    fmtTokens(task.tokensUsed),
    fmtDuration(task.durationSec),
  ].filter(Boolean);
  const modeTip = MODE_TIPS[state.composerMode] || MODE_TIPS.queue;

  return `
    <main class="detail-pane">
      <header class="doc-header">
        <div class="doc-title-row">
          <div class="doc-title tip-trigger" id="btnRenameTask" data-tip="点击自定义任务别名">${esc(task.title)}</div>
          <div class="doc-actions">
            <button class="text-btn violet tip-trigger tip-bottom-right tip-wrap" id="btnDiagnoseBlocker" data-tip="只读卡点诊断：fork read-only 提取进度与阻塞原因，不改文件">诊断</button>
            <button class="text-btn tip-trigger tip-bottom-right tip-wrap" id="btnOpenReadonlyModal" data-tip="向该会话发起自定义只读提问，不污染原上下文">只读</button>
            <button class="icon-btn tip-trigger tip-bottom-right" id="btnDetailPin" data-tip="${task.pinned ? '取消置顶' : '置顶此任务'}">${task.pinned ? '★' : '☆'}</button>
            <button class="icon-btn tip-trigger tip-bottom-right" id="btnDetailHide" data-tip="${task.hidden ? '从隐藏抽屉还原' : '隐藏到左下角抽屉'}">${task.hidden ? ICON_RESTORE : ICON_HIDE}</button>
          </div>
        </div>
        <div class="doc-meta">
          <span class="meta-mono tip-trigger" id="btnCopyThreadId" data-tip="点击复制完整 Thread ID">${esc(task.shortId)}</span>
          ${metaParts.map((p) => `<span class="meta-sep">·</span><span>${esc(p)}</span>`).join('')}
          ${git?.hasBlackboard ? `<span class="meta-sep">·</span><button class="text-btn violet" style="padding:0 4px" data-open-file="${esc(git.blackboardPath)}">BLACKBOARD</button>` : ''}
        </div>
      </header>

      <div class="sub-nav">
        <div class="sub-nav-tabs">
          <button class="sub-tab-btn ${state.detailSubTab === 'history' ? 'active' : ''}" data-subtab="history">动态</button>
          <button class="sub-tab-btn ${state.detailSubTab === 'ops' ? 'active' : ''}" data-subtab="ops">诊断${detail?.ops?.length ? ` (${detail.ops.length})` : ''}</button>
          <button class="sub-tab-btn ${state.detailSubTab === 'git' ? 'active' : ''}" data-subtab="git">变更${git?.files?.length ? ` (${git.files.length})` : ''}</button>
        </div>
        ${state.detailSubTab === 'history' ? `<button class="text-btn tip-trigger tip-bottom-right" id="btnToggleHistoryOrder" data-tip="切换动态时间顺序">${state.historyNewestFirst ? '↓ 最新' : '↑ 正序'}</button>` : ''}
      </div>

      <div class="detail-scroll">
        ${state.detailSubTab === 'history' ? renderHistory(detail, task) : ''}
        ${state.detailSubTab === 'ops' ? renderOps(detail, task) : ''}
        ${state.detailSubTab === 'git' ? renderGit(git) : ''}
      </div>

      <div class="composer-zone">
        <div class="composer-card">
          <textarea id="composerInput" placeholder="给 Codex 发消息…">${esc(state.composerText)}</textarea>
          <div class="composer-foot">
            <div class="composer-left">
              <span class="tip-trigger tip-top tip-wrap" data-tip="${esc(modeTip)}">
                <select class="mode-select" id="composerMode" aria-label="发送模式">
                  <option value="queue" ${state.composerMode === 'queue' ? 'selected' : ''}>排队唤醒</option>
                  <option value="resume" ${state.composerMode === 'resume' ? 'selected' : ''}>同步续跑</option>
                  ${task.dispatchTask ? `<option value="dispatch_resume" ${state.composerMode === 'dispatch_resume' ? 'selected' : ''}>Dispatch 续跑</option>` : ''}
                  <option value="readonly" ${state.composerMode === 'readonly' ? 'selected' : ''}>只读提问</option>
                </select>
              </span>
              <label class="dup-toggle tip-trigger tip-top tip-wrap" data-tip="默认拦截 60 秒内相同消息防误发；勾选后允许强制重发">
                <input id="chkAllowDup" type="checkbox" ${state.allowDuplicate ? 'checked' : ''} />
                重发
              </label>
            </div>
            <button class="send-circle tip-trigger tip-top-right" id="btnSendCodex" data-tip="发送给 Codex（Cmd / Ctrl + Enter）" ${state.sendingMessage ? 'disabled' : ''}>↑</button>
          </div>
        </div>
      </div>
    </main>
  `;
}

function renderSubagentDetailPane() {
  const a = selectedAgent();
  if (!a) {
    return `<main class="detail-pane"><div class="detail-empty"><button class="solid-btn" id="btnSpawnEmpty">+ 新建受管子代理</button></div></main>`;
  }
  const canSend = Boolean(state.capabilities?.message);
  const metaParts = [a.status, a.branch, a.model, a.effort, a.difficulty, fmtTokens(a.tokensUsed)].filter(Boolean);
  const sendText = `【受管子代理审计｜${a.taskId}】\n状态: ${a.status} · 分支: ${a.branch}\nWorktree: ${a.worktreePath}\n${a.summary || ''}`;

  return `
    <main class="detail-pane">
      <header class="doc-header">
        <div class="doc-title-row">
          <div class="doc-title">${esc(a.title)}</div>
          <div class="doc-actions">
            ${a.threadId ? `<button class="text-btn tip-trigger tip-bottom-right" data-jump-thread="${esc(a.threadId)}" data-tip="跳转到该子代理的实时对话流">打开会话</button>` : ''}
            ${canSend ? `<button class="text-btn violet tip-trigger tip-bottom-right" data-send-back="${esc(sendText)}" data-tip="把审计摘要发回当前 Antigravity 对话">发回对话</button>` : ''}
          </div>
        </div>
        <div class="doc-meta">
          <span class="meta-mono">${esc(a.taskId)}</span>
          ${metaParts.map((p) => `<span class="meta-sep">·</span><span>${esc(p)}</span>`).join('')}
        </div>
      </header>
      <div class="detail-scroll">
        <div class="feed-inner">
          <article class="op-card">
            <div class="msg-head">
              <span class="msg-role">执行摘要</span>
              <span>${a.verificationPassed ? '自测已通过' : esc(a.status)}</span>
            </div>
            <div class="msg-body">${renderMd(a.summary || '暂无摘要')}</div>
            <div class="clean-row-meta" style="margin-top:10px">${esc(a.worktreePath)}${a.worktreeExists ? '' : '（工作树已清理）'}</div>
          </article>

          ${a.changedFiles?.length ? `
            <div class="detail-section-title">改动文件 (${a.changedFiles.length})</div>
            ${a.changedFiles
              .map((f) => {
                const abs = a.worktreePath ? `${a.worktreePath.replace(/\/$/, '')}/${f}` : '';
                return `
                  <div class="git-row">
                    <span>${esc(f)}</span>
                    ${abs && a.worktreeExists ? `<button class="text-btn violet" data-open-file="${esc(abs)}">打开</button>` : ''}
                  </div>`;
              })
              .join('')}
          ` : ''}

          ${a.risks?.length ? `
            <div class="detail-section-title">待确认 / 风险提示</div>
            <article class="msg-card">
              <div class="msg-body"><ul>${a.risks.map((r) => `<li>${esc(r)}</li>`).join('')}</ul></div>
            </article>
          ` : ''}
        </div>
      </div>
    </main>
  `;
}

function renderCollabDetailPane() {
  const b = selectedBinding();
  if (!b) {
    return `<main class="detail-pane"><div class="detail-empty"><button class="solid-btn" id="btnNewBindingEmpty">+ 新建跨会话绑定</button></div></main>`;
  }
  const canSend = Boolean(state.capabilities?.message);
  const sendText = `【跨会话协作｜${b.changeKey}】\n目标: ${b.goalTitle}\n负责方: ${b.ownerRole} · 状态: ${b.status}\nCodex Thread: ${b.threadId || '-'}\n备注: ${b.notes || '-'}`;

  return `
    <main class="detail-pane">
      <header class="doc-header">
        <div class="doc-title-row">
          <div class="doc-title">${esc(b.changeKey)}</div>
          <div class="doc-actions">
            ${b.threadId ? `<button class="text-btn tip-trigger tip-bottom-right" data-jump-thread="${esc(b.threadId)}" data-tip="跳转到绑定的 Codex 会话">打开会话</button>` : ''}
            ${canSend ? `<button class="text-btn violet tip-trigger tip-bottom-right" data-send-back="${esc(sendText)}" data-tip="把绑定信息发回当前 Antigravity 对话">发回对话</button>` : ''}
            <button class="text-btn tip-trigger tip-bottom-right" data-del-binding="${esc(b.id)}" data-tip="删除此条跨会话绑定">删除</button>
          </div>
        </div>
        <div class="doc-meta">
          <span class="plan-tag">${esc(b.ownerRole)}</span>
          <span class="meta-sep">·</span><span>${esc(b.status)}</span>
          ${b.branch ? `<span class="meta-sep">·</span><span>${esc(b.branch)}</span>` : ''}
          ${b.threadId ? `<span class="meta-sep">·</span><span class="meta-mono">${esc(b.threadId.slice(0, 8))}</span>` : ''}
        </div>
      </header>
      <div class="detail-scroll">
        <div class="feed-inner">
          <article class="op-card">
            <div class="msg-head"><span class="msg-role">目标与边界</span></div>
            <div class="msg-body">${renderMd(b.goalTitle)}</div>
            ${b.notes ? `<div class="op-prompt" style="margin-top:10px;margin-bottom:0">${esc(b.notes)}</div>` : ''}
          </article>
          ${b.messages?.length ? `
            <div class="detail-section-title">交接记录 (${b.messages.length})</div>
            ${b.messages
              .map(
                (m) => `
                <article class="msg-card">
                  <div class="msg-head">
                    <span class="msg-role">${esc(m.author)}</span>
                    <span>${esc(clockTime(m.createdAt))}</span>
                  </div>
                  <div class="msg-body">${renderMd(m.content)}</div>
                </article>`
              )
              .join('')}
          ` : ''}
        </div>
      </div>
    </main>
  `;
}

function renderModal() {
  if (!state.modal) return '';
  const task = selectedTask();

  if (state.modal === 'spawn') {
    const cwd = task?.dispatchTask?.repoRoot || task?.cwd || '';
    return `
      <div class="modal-backdrop" data-close-modal="1">
        <div class="modal" onclick="event.stopPropagation()">
          <div class="modal-head"><span>新建受管子代理</span><button class="icon-btn" data-close-modal="1">✕</button></div>
          <div class="field"><label>工作目录</label><input id="mSpawnCwd" value="${esc(cwd)}" placeholder="/path/to/repo" /></div>
          <div class="field-grid-3">
            <div class="field"><label>质量</label><select id="mSpawnQuality"><option value="smart" selected>smart</option><option value="max">max</option><option value="balanced">balanced</option></select></div>
            <div class="field"><label>难度</label><select id="mSpawnDiff"><option value="auto" selected>auto</option><option value="low">low</option><option value="medium">medium</option><option value="hard">hard</option><option value="extreme">extreme</option></select></div>
            <div class="field"><label>隔离</label><select id="mSpawnIso"><option value="worktree" selected>worktree</option><option value="inplace">inplace</option></select></div>
          </div>
          <div class="field-grid-2">
            <div class="field"><label>Task ID（可选）</label><input id="mSpawnTaskId" placeholder="feat-auth-v1" /></div>
            <div class="field"><label>Change 绑定（可选）</label><input id="mSpawnChange" placeholder="change-auth" /></div>
          </div>
          <div class="field"><label>任务指令</label><textarea id="mSpawnPrompt" rows="4" placeholder="Read docs/BLACKBOARD.md, implement..., and run tests."></textarea></div>
          <div class="modal-foot"><button class="text-btn" data-close-modal="1">取消</button><button class="solid-btn" id="btnSubmitSpawn">启动</button></div>
        </div>
      </div>`;
  }

  if (state.modal === 'readonly') {
    return `
      <div class="modal-backdrop" data-close-modal="1">
        <div class="modal" onclick="event.stopPropagation()">
          <div class="modal-head"><span>只读提问</span><button class="icon-btn" data-close-modal="1">✕</button></div>
          <div class="field"><textarea id="mReadonlyPrompt" rows="4" placeholder="只读查询当前上下文（不修改文件、不污染原会话）…"></textarea></div>
          <div class="modal-foot"><button class="text-btn" data-close-modal="1">取消</button><button class="solid-btn" id="btnSubmitReadonly">提问</button></div>
        </div>
      </div>`;
  }

  if (state.modal === 'binding') {
    return `
      <div class="modal-backdrop" data-close-modal="1">
        <div class="modal" onclick="event.stopPropagation()">
          <div class="modal-head"><span>新建跨会话绑定</span><button class="icon-btn" data-close-modal="1">✕</button></div>
          <div class="field"><label>Change 标识</label><input id="mBindKey" placeholder="change-01" /></div>
          <div class="field"><label>目标</label><input id="mBindGoal" placeholder="验收目标" /></div>
          <div class="field-grid-2">
            <div class="field"><label>负责方</label><select id="mBindOwner"><option value="codex">codex</option><option value="antigravity">antigravity</option><option value="shared">shared</option></select></div>
            <div class="field"><label>状态</label><select id="mBindStatus"><option value="active">active</option><option value="blocked">blocked</option><option value="reviewing">reviewing</option><option value="completed">completed</option></select></div>
          </div>
          <div class="field"><label>Codex 会话 ID</label><input id="mBindThread" value="${esc(task?.id || '')}" /></div>
          <div class="field"><label>备注</label><textarea id="mBindNotes" rows="2"></textarea></div>
          <div class="modal-foot"><button class="text-btn" data-close-modal="1">取消</button><button class="solid-btn" id="btnSubmitBinding">保存</button></div>
        </div>
      </div>`;
  }

  if (state.modal === 'rename') {
    return `
      <div class="modal-backdrop" data-close-modal="1">
        <div class="modal" onclick="event.stopPropagation()">
          <div class="modal-head"><span>重命名任务</span><button class="icon-btn" data-close-modal="1">✕</button></div>
          <div class="field"><input id="mRenameInput" value="${esc(task?.customTitle || task?.title || '')}" /></div>
          <div class="modal-foot"><button class="text-btn" data-close-modal="1">取消</button><button class="solid-btn" id="btnSubmitRename">保存</button></div>
        </div>
      </div>`;
  }
  return '';
}

// ---------------- Main Render & Event Binding ----------------

function render() {
  const root = document.getElementById('root');
  if (!root) return;

  const activeEl = document.activeElement;
  const activeId = activeEl?.id || null;
  const selStart = typeof activeEl?.selectionStart === 'number' ? activeEl.selectionStart : null;
  const selEnd = typeof activeEl?.selectionEnd === 'number' ? activeEl.selectionEnd : null;

  const scrollTask = root.querySelector('.task-list')?.scrollTop ?? 0;
  const scrollDetail = root.querySelector('.detail-scroll')?.scrollTop ?? 0;
  const scrollHidden = root.querySelector('.hidden-drawer-body')?.scrollTop ?? 0;

  const s = state.stats;
  const cat = getCatState();
  const visibleAgyCount = state.tasks.filter((t) => !t.isSubagent && !t.hidden && t.isAgyDispatched).length;

  let workspaceHtml = '';
  if (state.activeTab === 'tasks') {
    workspaceHtml = `${renderTasksLeftRail()}${renderTaskDetailPane()}`;
  } else if (state.activeTab === 'subagents') {
    workspaceHtml = `${renderSubagentsLeftRail()}${renderSubagentDetailPane()}`;
  } else {
    workspaceHtml = `${renderCollabLeftRail()}${renderCollabDetailPane()}`;
  }

  root.innerHTML = `
    <div class="app-frame">
      <div class="app-shell">
        <header class="topbar">
          <nav class="nav-seg">
            <button class="nav-btn ${state.activeTab === 'tasks' ? 'active' : ''}" data-tab="tasks">
              任务${visibleAgyCount ? `<span class="nav-num">${visibleAgyCount}</span>` : ''}
            </button>
            <button class="nav-btn ${state.activeTab === 'subagents' ? 'active' : ''}" data-tab="subagents">
              子代理${s.managedCount ? `<span class="nav-num">${s.managedCount}</span>` : ''}
            </button>
            <button class="nav-btn ${state.activeTab === 'collab' ? 'active' : ''}" data-tab="collab">
              协作${s.collabCount ? `<span class="nav-num">${s.collabCount}</span>` : ''}
            </button>
          </nav>
          <div class="topbar-right">
            ${renderPixelCat({
              mode: cat.mode,
              label: cat.label,
              meowing: state.catMeowing,
              freezeLeft: state.catFreezeLeft,
              freezeFlip: state.catFreezeFlip,
            })}
            ${renderQuotaWidget()}
            <button class="icon-btn tip-trigger tip-bottom-right" id="btnRefresh" data-tip="立即刷新任务、进度与实时额度">${state.loadingSnapshot ? '·' : '↻'}</button>
            <button class="icon-btn accent tip-trigger tip-bottom-right" id="btnOpenSpawn" data-tip="新建受管 Codex 子代理（隔离 Worktree）">+</button>
          </div>
        </header>

        <div class="workspace">${workspaceHtml}</div>

        ${renderModal()}
        ${state.toast ? `<div class="toast ${esc(state.toast.kind)}">${esc(state.toast.text)}</div>` : ''}
      </div>
    </div>
  `;

  bindEvents();

  const nl = root.querySelector('.task-list');
  if (nl) nl.scrollTop = scrollTask;
  const nd = root.querySelector('.detail-scroll');
  if (nd) nd.scrollTop = scrollDetail;
  const nh = root.querySelector('.hidden-drawer-body');
  if (nh) nh.scrollTop = scrollHidden;

  if (activeId) {
    const el = document.getElementById(activeId);
    if (el && typeof el.focus === 'function') {
      el.focus();
      if (selStart !== null && typeof el.setSelectionRange === 'function') {
        try {
          el.setSelectionRange(selStart, selEnd ?? selStart);
        } catch {}
      }
    }
  }
}

function bindEvents() {
  document.getElementById('btnRefresh')?.addEventListener('click', () => {
    refreshSnapshot();
    refreshQuotaLive({ silent: true });
  });
  document.getElementById('btnQuotaRing')?.addEventListener('click', () => refreshQuotaLive());
  document.getElementById('btnQuotaRefresh')?.addEventListener('click', (e) => {
    e.stopPropagation();
    refreshQuotaLive();
  });

  // Pixel cat click: freezes at its exact live runway position, hops in place & pops '喵~'
  document.getElementById('btnCatPet')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    const walker = btn?.querySelector('.cat-walker');
    const svg = btn?.querySelector('.cat-svg');
    if (walker) {
      const curLeft = parseFloat(window.getComputedStyle(walker).left);
      if (!Number.isNaN(curLeft)) state.catFreezeLeft = curLeft;
    }
    if (svg) {
      const tf = window.getComputedStyle(svg).transform;
      // Matrix(a, b, c, d, tx, ty): negative 'a' means scaleX(-1)
      if (tf && tf.startsWith('matrix(')) {
        const a = parseFloat(tf.slice(7).split(',')[0]);
        if (!Number.isNaN(a)) state.catFreezeFlip = a < 0 ? -1 : 1;
      }
    }

    state.catMeowing = true;
    state.lastCatWakeMs = Date.now();
    if (state.catMeowTimer) clearTimeout(state.catMeowTimer);
    state.catMeowTimer = setTimeout(() => {
      state.catMeowing = false;
      state.catFreezeLeft = null;
      render();
    }, 2200);

    const active = state.tasks.find(
      (t) => !t.isSubagent && !t.hidden && (t.status.code === 'running' || t.status.code === 'blocked')
    );
    if (active && (state.activeTab !== 'tasks' || state.selectedThreadId !== active.id)) {
      state.activeTab = 'tasks';
      loadThreadDetail(active.id, { silent: true });
    } else {
      render();
    }
  });

  const openSpawn = () => {
    state.modal = 'spawn';
    render();
  };
  document.getElementById('btnOpenSpawn')?.addEventListener('click', openSpawn);
  document.getElementById('btnSpawnFromTab')?.addEventListener('click', openSpawn);
  document.getElementById('btnSpawnEmpty')?.addEventListener('click', openSpawn);

  const openBinding = () => {
    state.modal = 'binding';
    render();
  };
  document.getElementById('btnNewBinding')?.addEventListener('click', openBinding);
  document.getElementById('btnNewBindingEmpty')?.addEventListener('click', openBinding);

  document.querySelectorAll('[data-tab]').forEach((el) =>
    el.addEventListener('click', () => {
      state.activeTab = el.dataset.tab;
      render();
    })
  );
  document.querySelectorAll('[data-subtab]').forEach((el) =>
    el.addEventListener('click', () => {
      state.detailSubTab = el.dataset.subtab;
      render();
    })
  );

  document.getElementById('searchInput')?.addEventListener('input', (e) => {
    state.searchQuery = e.target.value;
    render();
  });
  document.getElementById('btnToggleDesktop')?.addEventListener('click', () => {
    state.showDesktopTasks = !state.showDesktopTasks;
    render();
  });
  document.getElementById('btnToggleHidden')?.addEventListener('click', () => {
    state.showHiddenDrawer = !state.showHiddenDrawer;
    render();
  });
  document.getElementById('btnToggleHistoryOrder')?.addEventListener('click', () => {
    state.historyNewestFirst = !state.historyNewestFirst;
    render();
    const sc = document.querySelector('.detail-scroll');
    if (sc) sc.scrollTop = 0;
  });

  document.querySelectorAll('[data-select-thread]').forEach((el) =>
    el.addEventListener('click', () => loadThreadDetail(el.dataset.selectThread))
  );
  document.querySelectorAll('[data-select-agent]').forEach((el) =>
    el.addEventListener('click', () => {
      state.selectedAgentId = el.dataset.selectAgent;
      render();
    })
  );
  document.querySelectorAll('[data-select-binding]').forEach((el) =>
    el.addEventListener('click', () => {
      state.selectedBindingId = el.dataset.selectBinding;
      render();
    })
  );

  document.querySelectorAll('[data-pin-thread]').forEach((el) =>
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const pinned = el.dataset.pinned === '1';
      updateThreadPref(el.dataset.pinThread, { pinned: !pinned }, !pinned ? '已置顶' : '已取消置顶');
    })
  );
  document.querySelectorAll('[data-hide-thread]').forEach((el) =>
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = el.dataset.hidden === '1';
      updateThreadPref(
        el.dataset.hideThread,
        { hidden: !isHidden },
        isHidden ? '已从隐藏抽屉还原' : '已收纳到左下角「已隐藏」抽屉'
      );
    })
  );

  const task = selectedTask();
  document.getElementById('btnDetailPin')?.addEventListener('click', () => {
    if (task) updateThreadPref(task.id, { pinned: !task.pinned }, !task.pinned ? '已置顶' : '已取消置顶');
  });
  document.getElementById('btnDetailHide')?.addEventListener('click', () => {
    if (task) {
      updateThreadPref(
        task.id,
        { hidden: !task.hidden },
        task.hidden ? '已从隐藏抽屉还原' : '已收纳到左下角「已隐藏」抽屉'
      );
    }
  });
  document.getElementById('btnCopyThreadId')?.addEventListener('click', () => task && copyText(task.id));
  document.getElementById('btnRenameTask')?.addEventListener('click', () => {
    state.modal = 'rename';
    render();
  });
  document.getElementById('btnOpenReadonlyModal')?.addEventListener('click', () => {
    state.modal = 'readonly';
    render();
  });
  const doDiag = () => task && triggerReadonly(task.id, '', 'diagnose_blocker');
  document.getElementById('btnDiagnoseBlocker')?.addEventListener('click', doDiag);
  document.getElementById('btnEmptyDiagnose')?.addEventListener('click', doDiag);

  const inp = document.getElementById('composerInput');
  inp?.addEventListener('input', (e) => {
    state.composerText = e.target.value;
  });
  inp?.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      sendComposer();
    }
  });
  document.getElementById('composerMode')?.addEventListener('change', (e) => {
    state.composerMode = e.target.value;
    render(); // refresh dynamic hover tooltip for the newly chosen mode
  });
  document.getElementById('chkAllowDup')?.addEventListener('change', (e) => {
    state.allowDuplicate = e.target.checked;
  });
  document.getElementById('btnSendCodex')?.addEventListener('click', sendComposer);

  document.querySelectorAll('[data-send-back]').forEach((el) =>
    el.addEventListener('click', () => sendBack(el.dataset.sendBack))
  );
  document.querySelectorAll('[data-open-file]').forEach((el) =>
    el.addEventListener('click', () => openFile(el.dataset.openFile))
  );
  document.querySelectorAll('[data-jump-thread]').forEach((el) =>
    el.addEventListener('click', () => {
      state.activeTab = 'tasks';
      loadThreadDetail(el.dataset.jumpThread);
    })
  );
  document.querySelectorAll('[data-del-binding]').forEach((el) =>
    el.addEventListener('click', async () => {
      try {
        await callTool('manage_collab_binding', { action: 'delete', id: el.dataset.delBinding });
        if (state.selectedBindingId === el.dataset.delBinding) state.selectedBindingId = null;
        await refreshSnapshot({ silent: true });
        showToast('已删除绑定');
      } catch (err) {
        showToast(err.message, 'error');
      }
    })
  );

  // Modals
  document.querySelectorAll('[data-close-modal]').forEach((el) =>
    el.addEventListener('click', () => {
      state.modal = null;
      render();
    })
  );

  document.getElementById('btnSubmitSpawn')?.addEventListener('click', async () => {
    try {
      const res = await callTool('spawn_codex_worker', {
        cwd: document.getElementById('mSpawnCwd')?.value?.trim(),
        prompt: document.getElementById('mSpawnPrompt')?.value?.trim(),
        quality: document.getElementById('mSpawnQuality')?.value,
        difficulty: document.getElementById('mSpawnDiff')?.value,
        isolation: document.getElementById('mSpawnIso')?.value,
        taskId: document.getElementById('mSpawnTaskId')?.value?.trim() || undefined,
        changeKey: document.getElementById('mSpawnChange')?.value?.trim() || undefined,
      });
      state.modal = null;
      state.activeTab = 'subagents';
      showToast('已启动子代理');
      await refreshSnapshot({ silent: true });
      if (res?.op?.id) pollOp(res.op.id, null);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('btnSubmitReadonly')?.addEventListener('click', async () => {
    const p = document.getElementById('mReadonlyPrompt')?.value?.trim();
    if (!p || !task) return;
    state.modal = null;
    render();
    await triggerReadonly(task.id, p, 'custom');
  });

  document.getElementById('btnSubmitBinding')?.addEventListener('click', async () => {
    const changeKey = document.getElementById('mBindKey')?.value?.trim();
    if (!changeKey) return showToast('请填写 Change 标识', 'error');
    try {
      const res = await callTool('manage_collab_binding', {
        action: 'upsert',
        changeKey,
        goalTitle: document.getElementById('mBindGoal')?.value?.trim() || changeKey,
        ownerRole: document.getElementById('mBindOwner')?.value,
        status: document.getElementById('mBindStatus')?.value,
        threadId: document.getElementById('mBindThread')?.value?.trim() || undefined,
        notes: document.getElementById('mBindNotes')?.value?.trim() || '',
        repoPath: task?.cwd || undefined,
        branch: task?.branch || undefined,
      });
      if (res?.binding?.id) state.selectedBindingId = res.binding.id;
      state.modal = null;
      await refreshSnapshot({ silent: true });
      showToast('已保存绑定');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('btnSubmitRename')?.addEventListener('click', async () => {
    if (!task) return;
    await updateThreadPref(task.id, { customTitle: document.getElementById('mRenameInput')?.value ?? '' }, '已重命名');
    state.modal = null;
    render();
  });
}

// ---------------- Host Lifecycle ----------------

function scheduleAutoRefresh() {
  const active = selectedTask();
  const hot =
    state.stats.runningCount > 0 ||
    state.stats.runningOpsCount > 0 ||
    active?.status?.code === 'running';
  const ms = hot ? 4_000 : 12_000;
  if (state.autoRefreshTimer && state.lastPollMs === ms) return;
  if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);
  state.lastPollMs = ms;
  state.autoRefreshTimer = setInterval(() => {
    if (!state.modal && !state.sendingMessage) refreshSnapshot({ silent: true });
  }, ms);
}

app.ontoolinput = () => {};

app.ontoolresult = (result) => {
  const sc = result?.structuredContent;
  if (sc) {
    if (sc.initialTab) state.activeTab = sc.initialTab;
    if (sc.initialThreadId) state.selectedThreadId = sc.initialThreadId;
    if (sc.initialQuery) state.searchQuery = sc.initialQuery;
    if (sc.stats) state.stats = sc.stats;
    if (sc.connected !== undefined) state.connected = sc.connected;
  }
  refreshSnapshot();
};

app.onhostcontextchanged = (ctx) => {
  if (ctx?.theme) {
    applyDocumentTheme(ctx.theme);
    document.documentElement.setAttribute('data-theme', ctx.theme);
  }
  if (ctx?.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
};

async function boot() {
  await app.connect();
  state.capabilities = app.getHostCapabilities() || {};
  const ctx = app.getHostContext();
  if (ctx?.theme) {
    applyDocumentTheme(ctx.theme);
    document.documentElement.setAttribute('data-theme', ctx.theme);
  }
  if (ctx?.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
  render();
  await refreshSnapshot();
  scheduleAutoRefresh();
}

boot().catch((err) => {
  const root = document.getElementById('root');
  if (root) root.innerHTML = `<div class="boot-loading">${esc(err.message)}</div>`;
});
