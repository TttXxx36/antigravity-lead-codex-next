import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { validateWindowsPath, normalizePath, runtimePaths, resolveExecutable, buildRuntimeEnv } from '../plugins/codex-console/server/platform.mjs';

test('Windows lexical reserved names and long paths', () => {
  for (const p of ['C:\\tmp\\NUL.txt','C:\\tmp\\COM1','C:\\tmp\\bad.','C:\\tmp\\a:b','\\\\?\\C:\\tmp\\a','C:\\tmp\\LPT².log','C:\\tmp\\bad '])
    assert.throws(() => validateWindowsPath(p), /Windows/);
  validateWindowsPath('C:\\中文 空格\\普通文件.txt');
  validateWindowsPath('C:\\' + Array(5).fill('a'.repeat(70)).join('\\'));
  assert.equal(normalizePath('C:\\中文 空格\\folder\\..\\state', {platform:'win32'}), 'C:\\中文 空格\\state');
});

test('custom roots and env path separator', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'd03-platform-'));
  try {
    const root = path.join(home, '中文 空格');
    const long = path.join(root, ...Array.from({length:5}, (_,i)=>String.fromCharCode(97+i).repeat(65)));
    fs.mkdirSync(long, {recursive:true});
    const file = path.join(normalizePath(long), '中文 evidence.txt');
    assert.ok(file.length > 260);
    fs.writeFileSync(file, 'fixture', 'utf8');
    assert.equal(fs.readFileSync(file, 'utf8'), 'fixture');
    fs.unlinkSync(file);
    const env = {PATH: [root, long].join(path.delimiter), CODEX_HOME: root, GEMINI_CONFIG_DIR: path.join(root,'config'), AGY_DISPATCH_STATE_DIR: long};
    const p = runtimePaths(env,home);
    assert.equal(p.codexHome,root);
    assert.equal(p.dispatchStateDir,long);
    assert.equal(p.geminiConfigDir,env.GEMINI_CONFIG_DIR);
    const next = buildRuntimeEnv(env,home);
    assert.deepEqual(next.PATH.split(path.delimiter).slice(0,2),[root,long]);
    assert.equal(next.PYTHONUTF8,'1');
  } finally { fs.rmSync(home,{recursive:true,force:true}); }
});

test('native explicit executable and missing override fail closed', () => {
  assert.equal(resolveExecutable('codex',{CODEX_BIN:process.execPath}),path.resolve(process.execPath));
  assert.equal(resolveExecutable('codex',{CODEX_BIN:path.join(os.tmpdir(),'d03-no-such-exe-8137.exe'),PATH:path.dirname(process.execPath)}),null);
  assert.equal(resolveExecutable('codex',{PATH:'.'}),null);
});

test('Windows rejects cmd wrapper without executing it', {skip:process.platform!=='win32'}, () => {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'d03-wrapper-'));
  try {
    const p=path.join(dir,'codex.cmd'); fs.writeFileSync(p,'@exit /b 0');
    assert.equal(resolveExecutable('codex',{CODEX_BIN:p}),null);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
