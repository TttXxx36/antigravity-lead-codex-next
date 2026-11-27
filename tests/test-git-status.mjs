import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { parsePorcelainZ } from '../plugins/codex-console/server/git-status.mjs';

test('literal names and rename ordering',()=>{
 const rows=parsePorcelainZ('R  新 文件.txt\0旧 文件.txt\0?? leading and trailing \0 M quote"line\n.txt\0','/fixture');
 assert.equal(rows[0].file,'新 文件.txt');assert.equal(rows[0].originalFile,'旧 文件.txt');
 assert.equal(rows[1].file,'leading and trailing ');
 assert.equal(rows[2].file,'quote"line\n.txt');
 assert.throws(()=>parsePorcelainZ('R  new\0','/fixture'));
 assert.throws(()=>parsePorcelainZ('?? truncated','/fixture'));
});
test('real git porcelain -z rename on native filesystem',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'d08-git-'));
 const env={...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:os.devNull,GIT_TERMINAL_PROMPT:'0'};
 const git=(...args)=>execFileSync('git',['-c','core.hooksPath='+path.join(root,'no-hooks'),'-c','user.name=Mock','-c','user.email=mock@example.invalid',...args],{cwd:root,env,encoding:'utf8'});
 try{
  git('init','-b','main');
  fs.writeFileSync(path.join(root,'旧 文件.txt'),'fixture');
  git('add','--','旧 文件.txt');git('commit','-m','fixture');
  git('mv','--','旧 文件.txt','新 文件.txt');
  fs.writeFileSync(path.join(root,'extra space.txt'),'x');
  const rows=parsePorcelainZ(git('status','--porcelain=v1','-z'),root);
  assert.ok(rows.some(x=>x.file==='新 文件.txt'&&x.originalFile==='旧 文件.txt'&&x.xy==='R'));
  assert.ok(rows.some(x=>x.file==='extra space.txt'&&x.xy==='??'));
 }finally{fs.rmSync(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});}
});
