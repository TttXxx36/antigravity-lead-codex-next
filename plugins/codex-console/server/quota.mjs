import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { runtimePaths } from './platform.mjs';

const CODEX_HOME = runtimePaths().codexHome;
const CACHE_TTL_MS = 60_000;

function formatWindowMeta(windowMins) {
  const mins = Number(windowMins || 0);
  if (!mins) return { key: 'unknown', label: '周期额度', shortLabel: '额度' };
  if (mins <= 360) {
    const hrs = Math.round(mins / 60) || 5;
    return { key: '5h', label: `${hrs} 小时额度`, shortLabel: `${hrs}h` };
  }
  if (mins >= 1440) {
    const days = Math.round(mins / 1440);
    return { key: 'weekly', label: days === 7 ? '周额度 (7天)' : `${days} 天额度`, shortLabel: `${days}d` };
  }
  const hrs = Math.round(mins / 60);
  return { key: `${hrs}h`, label: `${hrs} 小时额度`, shortLabel: `${hrs}h` };
}

function normalizeWindow(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const usedRaw = raw.usedPercent ?? raw.used_percent;
  if (typeof usedRaw !== 'number' || Number.isNaN(usedRaw)) return null;
  const windowMins = raw.windowDurationMins ?? raw.window_minutes ?? 0;
  const resetsAtSec = raw.resetsAt ?? raw.resets_at ?? null;
  const usedPercent = Math.max(0, Math.min(100, Math.round(usedRaw * 10) / 10));
  const remainingPercent = Math.max(0, Math.min(100, Math.round((100 - usedPercent) * 10) / 10));
  const meta = formatWindowMeta(windowMins);
  return {
    key: meta.key,
    label: meta.label,
    shortLabel: meta.shortLabel,
    windowMinutes: Number(windowMins || 0),
    usedPercent,
    remainingPercent,
    resetsAtMs: resetsAtSec ? Number(resetsAtSec) * 1000 : null,
  };
}

function normalizeRateLimitsPayload(rl, extra = {}) {
  if (!rl || typeof rl !== 'object') return null;
  const windows = [];
  const p = normalizeWindow(rl.primary);
  const s = normalizeWindow(rl.secondary);
  if (p) windows.push(p);
  if (s) windows.push(s);
  if (!windows.length) return null;

  // Sort shortest window first (e.g. 5h before 7d) for display inside popover
  windows.sort((a, b) => (a.windowMinutes || 999999) - (b.windowMinutes || 999999));

  // Bottleneck = minimum remaining percent across available windows (5h vs weekly)
  const bottleneck = windows.reduce(
    (min, cur) => (cur.remainingPercent < min.remainingPercent ? cur : min),
    windows[0]
  );

  const credits = rl.credits
    ? {
        hasCredits: Boolean(rl.credits.hasCredits ?? rl.credits.has_credits),
        unlimited: Boolean(rl.credits.unlimited),
        balance: String(rl.credits.balance ?? '0'),
      }
    : null;

  return {
    available: true,
    source: extra.source || 'rollout',
    planType: rl.planType ?? rl.plan_type ?? null,
    limitId: rl.limitId ?? rl.limit_id ?? 'codex',
    bottleneck,
    windows,
    credits,
    resetCreditsAvailable: Number(extra.resetCreditsAvailable || 0),
    spendControlReached: Boolean(rl.spendControlReached ?? rl.spend_control_reached),
    updatedAtMs: extra.updatedAtMs || Date.now(),
  };
}

function collectRecentRollouts(dir, limit = 10) {
  if (!fs.existsSync(dir)) return [];
  const files = [];
  const walk = (d, depth = 0) => {
    if (depth > 4) return;
    let entries;
    try {
      entries = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) {
        walk(full, depth + 1);
      } else if (e.isFile() && e.name.endsWith('.jsonl')) {
        try {
          const st = fs.statSync(full);
          files.push({ path: full, mtimeMs: st.mtimeMs });
        } catch {
          // ignore
        }
      }
    }
  };
  walk(dir, 0);
  files.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return files.slice(0, limit);
}

function readTailLines(filePath, maxBytes = 128 * 1024) {
  let fd = null;
  try {
    const stat = fs.statSync(filePath);
    const start = Math.max(0, stat.size - maxBytes);
    const length = stat.size - start;
    if (length <= 0) return [];
    const buf = Buffer.alloc(length);
    fd = fs.openSync(filePath, 'r');
    fs.readSync(fd, buf, 0, length, start);
    return buf.toString('utf8').split('\n');
  } catch {
    return [];
  } finally {
    if (fd !== null) {
      try {
        fs.closeSync(fd);
      } catch {
        // ignore
      }
    }
  }
}

export function readQuotaFromRollouts(codexHome = CODEX_HOME) {
  const sessionsDir = path.join(codexHome, 'sessions');
  const rollouts = collectRecentRollouts(sessionsDir, 10);
  for (const file of rollouts) {
    const lines = readTailLines(file.path);
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i];
      if (!line || !line.includes('"rate_limits"')) continue;
      try {
        const obj = JSON.parse(line);
        const rl = obj?.payload?.rate_limits;
        if (!rl) continue;
        const tsMs = obj.timestamp ? Date.parse(obj.timestamp) : file.mtimeMs;
        const normalized = normalizeRateLimitsPayload(rl, {
          source: 'rollout',
          updatedAtMs: Number.isNaN(tsMs) ? file.mtimeMs : tsMs,
        });
        if (normalized) return normalized;
      } catch {
        // ignore malformed line
      }
    }
  }
  return {
    available: false,
    source: 'none',
    planType: null,
    bottleneck: null,
    windows: [],
    credits: null,
    resetCreditsAvailable: 0,
    updatedAtMs: Date.now(),
  };
}

export function fetchQuotaFromAppServer(codexBin, env, timeoutMs = 5500) {
  return new Promise((resolve) => {
    if (!codexBin) return resolve(null);
    let settled = false;
    const finish = (val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        child.kill('SIGTERM');
      } catch {
        // ignore
      }
      resolve(val);
    };

    let child;
    try {
      child = spawn(codexBin, ['app-server', '--stdio'], {
        env,
        stdio: ['pipe', 'pipe', 'ignore'],
      });
    } catch {
      return resolve(null);
    }

    const timer = setTimeout(() => finish(null), timeoutMs);
    let buf = '';

    child.on('error', () => finish(null));
    child.on('exit', () => finish(null));

    child.stdout.on('data', (chunk) => {
      buf += chunk.toString('utf8');
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (!line) continue;
        try {
          const msg = JSON.parse(line);
          if (msg.id === 1 && msg.result) {
            child.stdin.write(
              JSON.stringify({
                jsonrpc: '2.0',
                id: 2,
                method: 'account/rateLimits/read',
                params: {},
              }) + '\n'
            );
          } else if (msg.id === 2) {
            const rl = msg.result?.rateLimits || msg.result?.rateLimitsByLimitId?.codex;
            const resetCreditsAvailable = msg.result?.rateLimitResetCredits?.availableCount || 0;
            const normalized = normalizeRateLimitsPayload(rl, {
              source: 'live',
              resetCreditsAvailable,
              updatedAtMs: Date.now(),
            });
            finish(normalized);
            return;
          }
        } catch {
          // ignore non-JSON line
        }
      }
    });

    try {
      child.stdin.write(
        JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'initialize',
          params: {
            clientInfo: { name: 'codex-console', version: '1.0.0' },
            capabilities: {},
          },
        }) + '\n'
      );
    } catch {
      finish(null);
    }
  });
}

export class QuotaTracker {
  constructor({ codexBin, env, codexHome = CODEX_HOME } = {}) {
    this.codexBin = codexBin;
    this.env = env;
    this.codexHome = codexHome;
    this.cachedLive = null;
    this.lastLiveAttemptMs = 0;
    this.inFlight = null;
  }

  /**
   * Non-blocking snapshot for fast UI polling: returns live cache if fresh,
   * otherwise returns rollout fallback immediately and refreshes live in background.
   */
  getFastQuota() {
    const now = Date.now();
    if (this.cachedLive && now - this.cachedLive.updatedAtMs < CACHE_TTL_MS) {
      return this.cachedLive;
    }
    if (now - this.lastLiveAttemptMs > CACHE_TTL_MS && !this.inFlight) {
      this._triggerBackgroundRefresh();
    }
    if (this.cachedLive) return this.cachedLive;
    return readQuotaFromRollouts(this.codexHome);
  }

  async refreshLive() {
    if (this.inFlight) return this.inFlight;
    this.lastLiveAttemptMs = Date.now();
    this.inFlight = fetchQuotaFromAppServer(this.codexBin, this.env)
      .then((res) => {
        if (res && res.available) {
          this.cachedLive = res;
          return res;
        }
        return this.cachedLive || readQuotaFromRollouts(this.codexHome);
      })
      .finally(() => {
        this.inFlight = null;
      });
    return this.inFlight;
  }

  _triggerBackgroundRefresh() {
    this.refreshLive().catch(() => {});
  }
}
