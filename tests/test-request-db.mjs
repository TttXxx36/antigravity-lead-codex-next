import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { ConsoleDB } from '../plugins/codex-console/server/console-db.mjs';
import { classifyKeyedResult } from '../plugins/codex-console/server/outcome.mjs';

const options={requestId:'Req-1',identity:['run','repo','task-1',1,'synthetic'],opType:'spawn_worker',prompt:'synthetic'};
const temp=()=>fs.mkdtempSync(path.join(os.tmpdir(),'d13-request-'));
test('durable reservation returns original across restart, no cross-scope leakage',()=>{
 const root=temp();
 let db=new ConsoleDB(root);
 try {
  const first=db.reserveRequest(options);
  assert.equal(first.created,true);
  assert.equal(db.reserveRequest({...options,requestId:'req-1'}).op.id,first.op.id);
  const conflict=db.reserveRequest({...options,identity:['other']});
  assert.equal(conflict.conflict,true);assert.deepEqual(Object.keys(conflict.op).sort(),['id','status']);
  db.db.close();db=new ConsoleDB(root);
  const old=db.reserveRequest(options);
  assert.equal(old.created,false);assert.equal(old.op.id,first.op.id);
  assert.equal(old.op.status,'running'); // same live owner, even after reopening DB
  db.finishOp(old.op.id,{status:'succeeded'});
  assert.equal(db.getOp(old.op.id).status,'succeeded');
  assert.equal(db.listOps().length,1);
 }finally{db.db.close();fs.rmSync(root,{recursive:true,force:true});}
});
test('two Node processes reserve exactly one console operation',async()=>{
 const root=temp();
 const initial=new ConsoleDB(root);initial.db.close();
 const moduleUrl=new URL('../plugins/codex-console/server/console-db.mjs',import.meta.url).href;
 const source='import {ConsoleDB} from '+JSON.stringify(moduleUrl)+';const d=new ConsoleDB(process.argv[1]);const r=d.reserveRequest(JSON.parse(process.argv[2]));console.log(JSON.stringify({created:r.created,id:r.op.id}));d.db.close()';
 const run=()=>new Promise((resolve,reject)=>{
  const child=spawn(process.execPath,['--no-warnings','--input-type=module','-e',source,root,JSON.stringify(options)]);
  let out='',err='';child.stdout.on('data',c=>out+=c);child.stderr.on('data',c=>err+=c);
  child.once('error',reject);child.once('close',rc=>{try{assert.equal(rc,0,err);resolve(JSON.parse(out));}catch(e){reject(e);}});
 });
 try{
  const [a,b]=await Promise.all([run(),run()]);
  assert.equal(Number(a.created)+Number(b.created),1);
  assert.equal(a.id,b.id);
  const db=new ConsoleDB(root);try{assert.equal(db.listOps().length,1);}finally{db.db.close();}
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('keyed result identity and duplicate receipt never imply independent verification',()=>{
 const v={version:2,task_id:'task-1',rev:1,base_rev:0,exit_code:0,
  process_status:'exited',task_status:'completed',verification_status:'passed',
  process_error:false,summary:'synthetic',result_ref:'runs/task-1/result.json'};
 assert.equal(classifyKeyedResult(0,v,'task-1',1).status,'succeeded');
 assert.equal(classifyKeyedResult(0,v,'task-1',1).verificationStatus,'unknown');
 for(const bad of [{...v,rev:2},{...v,task_id:'other'},{...v,result_ref:'runs/other/result.json'},{duplicate:true,original_exit_code:0}]){
  assert.equal(classifyKeyedResult(0,bad,'task-1',1).status,'failed');
 }
 assert.equal(classifyKeyedResult(1,v,'task-1',1).status,'failed');
 assert.equal(classifyKeyedResult(0,v,'task-1',1,true).status,'failed');
});

test('opening a second MCP instance preserves live keyed owner; dead owner cannot relaunch',async()=>{
 const root=temp();
 const moduleUrl=new URL('../plugins/codex-console/server/console-db.mjs',import.meta.url).href;
 const source='import {ConsoleDB} from '+JSON.stringify(moduleUrl)+';const d=new ConsoleDB(process.argv[1]);const r=d.reserveRequest(JSON.parse(process.argv[2]));console.log(r.op.id);process.stdin.resume();process.stdin.on("end",()=>{d.close();process.exit(0)})';
 const child=spawn(process.execPath,['--no-warnings','--input-type=module','-e',source,root,JSON.stringify(options)],{stdio:['pipe','pipe','pipe']});
 const closed=new Promise(resolve=>child.once('close',resolve));
 try {
  const id=await new Promise((resolve,reject)=>{let out='';child.stdout.on('data',c=>{out+=c;if(out.includes('\n'))resolve(out.trim())});child.once('error',reject);child.once('close',rc=>reject(new Error('owner exited '+rc)))});
  const observer=new ConsoleDB(root);
  try {const duplicate=observer.reserveRequest(options);assert.equal(duplicate.created,false);assert.equal(duplicate.op.id,id);assert.equal(duplicate.op.status,'running');}
  finally{observer.close()}
  child.stdin.end();assert.equal(await closed,0);
  const restarted=new ConsoleDB(root);
  try {const duplicate=restarted.reserveRequest(options);assert.equal(duplicate.created,false);assert.equal(duplicate.op.id,id);assert.equal(duplicate.op.status,'interrupted');}
  finally{restarted.close()}
 }finally{child.stdin.end();await closed;fs.rmSync(root,{recursive:true,force:true})}
});
