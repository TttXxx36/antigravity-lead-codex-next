import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {QueryCache,DisplayReportCache,displayStamp,revisionEnvelope} from '../plugins/codex-console/server/query-cache.mjs';

test('same-key concurrent calls coalesce; callers cannot mutate cache',async()=>{
 const c=new QueryCache();let reads=0;
 const args={stamp:()=> 's',load:async()=>{reads++;return {n:reads};}};
 const [a,b]=await Promise.all([c.get('x',args),c.get('x',args)]);
 a.n=99;assert.equal(b.n,1);assert.equal((await c.get('x',args)).n,1);assert.equal(reads,1);
});
test('source revision, TTL and manual refresh invalidate',async()=>{
 let now=0,stamp='a',reads=0;const c=new QueryCache({ttlMs:50,clock:()=>now});
 const args={stamp:()=>stamp,load:()=>({n:++reads})};
 assert.equal((await c.get('x',args)).n,1);stamp='b';
 assert.equal((await c.get('x',args)).n,2);now=51;
 assert.equal((await c.get('x',args)).n,3);assert.equal((await c.get('x',{...args,force:true})).n,4);
});
test('failed, unstable, unknown and oversized results are not cached',async()=>{
 const c=new QueryCache({maxBytes:40});let reads=0;
 const load=()=>({n:++reads});let s='a';
 await c.get('bad',{stamp:()=>s,load,cacheable:()=>false});await c.get('bad',{stamp:()=>s,load});
 assert.equal(reads,2);
 await c.get('unknown',{stamp:()=>null,load});await c.get('unknown',{stamp:()=>null,load});assert.equal(reads,4);
 await c.get('unstable',{stamp:()=>s,load:()=>{s='b';return load();}});await c.get('unstable',{stamp:()=>s,load});assert.equal(reads,6);
 await assert.rejects(c.get('error',{stamp:()=>s,load:()=>{throw Error('broken');}}),/broken/);
 await c.get('large',{stamp:()=>s,load:()=>({x:'x'.repeat(100)})});assert.equal(c.entries.has('large'),false);
});
test('bounded cache and WAL/marker changes',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'d16-'));
 try{
  const db=path.join(dir,'native.sqlite'),marker=path.join(dir,'state.json');
  fs.writeFileSync(db,'fixture');fs.writeFileSync(marker,'{"tasks":{}}');
  const a=displayStamp([db],dir);assert.notEqual(a,null);
  fs.writeFileSync(db+'-wal','changed');const b=displayStamp([db],dir);assert.notEqual(a,b);
  fs.writeFileSync(marker,'{"storage":"sqlite-v1","database":"dispatch-state-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.sqlite"}');
  const c=displayStamp([db],dir);fs.writeFileSync(path.join(dir,'dispatch-state-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.sqlite-wal'),'next');assert.notEqual(c,displayStamp([db],dir));
  fs.writeFileSync(marker,'broken');assert.equal(displayStamp([db],dir),null);
  const cache=new QueryCache({maxEntries:2});for(let i=0;i<5;i++)await cache.get(String(i),{stamp:()=> 'x',load:()=>({i})});assert.equal(cache.entries.size,2);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('unchanged revision omits payload; actual changes visible',()=>{
 const first=revisionEnvelope({tasks:[{id:1,status:'running'}],fetchedAt:1});
 const same=revisionEnvelope({tasks:[{id:1,status:'running'}],fetchedAt:2},first.revision);
 assert.deepEqual(same,{revision:first.revision,changed:false});
 const changed=revisionEnvelope({tasks:[{id:1,status:'completed'}],fetchedAt:2},first.revision);assert.equal(changed.changed,true);
});

test('report cache honors mtime, rejects stale digest and unsafe identities',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'d16-report-'));
 try{
  const dir=path.join(root,'runs','task-1');fs.mkdirSync(dir,{recursive:true});
  const file=path.join(dir,'result.json');
  const cache=new DisplayReportCache(root);
  const task={task_id:'task-1',run_dir:dir,status:'completed'};
  fs.writeFileSync(file,JSON.stringify({report:{summary:'a'}}));
  assert.equal(cache.read(task).report.summary,'a');assert.equal(cache.read(task).report.summary,'a');assert.equal(cache.reads,1);
  fs.writeFileSync(file,JSON.stringify({report:{summary:'changed'}}));
  assert.equal(cache.read(task).report.summary,'changed');assert.equal(cache.reads,2);
  assert.equal(cache.read({...task,result_ref:{turn:null,sha256:'0'.repeat(64)}}),null);
  assert.equal(cache.read({...task,task_id:'../bad'}),null);
  assert.equal(cache.read({...task,status:'running'}),null);
  fs.unlinkSync(file);assert.equal(cache.read(task),null);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
