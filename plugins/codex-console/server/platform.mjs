import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const reserved = /^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$/i;

export function validateWindowsPath(value) {
  const raw = String(value).replaceAll('/', '\\');
  if (raw.startsWith('\\\\?\\') || raw.startsWith('\\\\.\\')) throw new Error('Windows device namespace not supported');
  const root = path.win32.parse(raw).root;
  const rest = raw.slice(root.length);
  for (const part of rest.split('\\')) {
    if (!part || part === '.' || part === '..') continue;
    if (/[ .]$/.test(part) || /[<>:"|?*\x00-\x1f]/.test(part) ||
        reserved.test(part.split('.')[0].trimEnd())) throw new Error('Invalid or reserved Windows path component');
  }
}

export function normalizePath(value, { platform = process.platform, home = os.homedir() } = {}) {
  if (typeof value !== 'string' || !value || value.includes('\0')) throw new Error('Invalid empty/NUL path');
  const p = platform === 'win32' ? path.win32 : path;
  let raw = value;
  if (raw === '~') raw = home;
  else if (raw.startsWith('~/') || (platform === 'win32' && raw.startsWith('~\\'))) raw = p.join(home, raw.slice(2));
  if (platform === 'win32') validateWindowsPath(raw);
  return p.resolve(raw);
}

export function runtimePaths(env = process.env, home = os.homedir()) {
  return {
    codexHome: normalizePath(env.CODEX_HOME || path.join(home, '.codex'), { home }),
    dispatchStateDir: normalizePath(env.AGY_DISPATCH_STATE_DIR || path.join(home, '.local', 'state', 'multi-agent-dispatch'), { home }),
    geminiConfigDir: normalizePath(env.GEMINI_CONFIG_DIR || path.join(home, '.gemini', 'config'), { home }),
  };
}

const unixFallbacks = (name, home) => ({
  codex: ['/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex',
    path.join(home, '.local', 'bin', 'codex'), path.join(home, '.npm-global', 'bin', 'codex'),
    path.join(home, '.volta', 'bin', 'codex'), '/opt/homebrew/bin/codex', '/usr/local/bin/codex'],
  python: [path.join(home, '.local', 'bin', 'python3'), '/opt/homebrew/bin/python3', '/usr/local/bin/python3', '/usr/bin/python3'],
  git: ['/usr/bin/git', '/opt/homebrew/bin/git', '/usr/local/bin/git'],
})[name] || [];

export function pathValue(env) {
  return process.platform === 'win32' ? (Object.entries(env).find(([key]) => key.toUpperCase() === 'PATH')?.[1] || '') : (env.PATH || '');
}

export function resolveExecutable(name, env = process.env, home = os.homedir()) {
  const override = { codex: 'CODEX_BIN', python: 'PYTHON_BIN', git: 'GIT_BIN', node: 'NODE_BIN' }[name];
  const windows = process.platform === 'win32';
  const leaf = windows ? name + '.exe' : name === 'python' ? 'python3' : name;
  const explicit = override && env[override];
  const dirs = pathValue(env).split(path.delimiter).map(p => p.replace(/^"|"$/g, '')).filter(p => path.isAbsolute(p));
  const candidates = explicit ? [explicit] : [...dirs.map(p => path.join(p, leaf)), ...(windows ? [] : unixFallbacks(name, home))];
  for (const raw of candidates) {
    try {
      const candidate = normalizePath(raw, { home });
      if (windows && path.extname(candidate).toLowerCase() !== '.exe') continue;
      if (!fs.statSync(candidate).isFile()) continue;
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {}
  }
  return null; // explicit invalid override must never silently fall back
}

export function buildRuntimeEnv(env = process.env, home = os.homedir()) {
  const dirs = process.platform === 'win32' ? [] : [
    path.join(home, '.local', 'bin'), path.join(home, '.npm-global', 'bin'),
    path.join(home, '.volta', 'bin'), '/opt/homebrew/bin', '/usr/local/bin'];
  const result = { ...env };
  if (process.platform === 'win32') {
    for (const key of Object.keys(result)) if (key.toUpperCase() === 'PATH') delete result[key];
  }
  const paths = runtimePaths(env, home);
  return { ...result, PATH: [pathValue(env), ...dirs].filter(Boolean).join(path.delimiter),
    CODEX_HOME: paths.codexHome, AGY_DISPATCH_STATE_DIR: paths.dispatchStateDir,
    GEMINI_CONFIG_DIR: paths.geminiConfigDir, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' };
}
