import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const entry = path.resolve(process.argv[2] || '');
if (!fs.statSync(entry).isFile()) throw new Error('MCP entry missing');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'alc-smoke-'));
let child, closed;
try {
  const env = {};
  for (const key of ['PATH','Path','SystemRoot','WINDIR','COMSPEC','TEMP','TMP']) {
    if (process.env[key] !== undefined) env[key] = process.env[key];
  }
  Object.assign(env, {HOME:root,USERPROFILE:root,CODEX_HOME:path.join(root,'codex'),
    AGY_DISPATCH_STATE_DIR:path.join(root,'dispatch'),GEMINI_CONFIG_DIR:path.join(root,'config'),
    CODEX_BIN:process.execPath,PYTHONUTF8:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:os.devNull});
  child=spawn(process.execPath,['--no-warnings',entry,'--data-dir',path.join(root,'plugin-data')],{
    cwd:root,env,stdio:['pipe','pipe','pipe']});
  closed=new Promise(resolve=>child.once('close',resolve));
  child.stderr.resume();
  const pending=new Map();let buffer='';
  child.stdout.setEncoding('utf8');
  child.stdout.on('data',chunk=>{
    buffer+=chunk;
    if(buffer.length>2*1024*1024){child.kill();return;}
    for(let i;(i=buffer.indexOf('\n'))>=0;){
      const line=buffer.slice(0,i);buffer=buffer.slice(i+1);
      if(!line.trim())continue;
      try {
        const msg=JSON.parse(line);const fn=pending.get(msg.id);
        if(fn){pending.delete(msg.id);fn(msg);}
      } catch { child.kill(); }
    }
  });
  child.stdin.on('error',()=>{});
  child.on('error',()=>{for(const fn of pending.values()) fn({error:{message:'spawn failed'}});pending.clear();});
  const rpc=(id,method,params={})=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error('RPC timeout: '+method));},5000);
    pending.set(id,msg=>{clearTimeout(timer);msg.error?reject(new Error('RPC error: '+method)):resolve(msg.result);});
    child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');
  });
  const init=await rpc(1,'initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'alc-doctor',version:'1'}});
  if(!init?.capabilities?.tools||!init?.capabilities?.resources)throw new Error('MCP capabilities missing');
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized'})+'\n');
  const list=await rpc(2,'tools/list');
  if(!Array.isArray(list?.tools)||!list.tools.length)throw new Error('MCP tools missing');
  child.kill();
  await closed;
  console.log(JSON.stringify({status:'PASS',protocolVersion:init.protocolVersion,tools:list.tools.length,real_model_calls:0}));
} finally {
  if(child&&child.exitCode===null&&!child.killed)child.kill();
  if(closed) await closed;
  // The only removed directory is this process's newly created synthetic fixture.
  fs.rmSync(root,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
