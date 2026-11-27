import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { classifyManagedResult, watchOwnedChild } from '../plugins/codex-console/server/outcome.mjs';
import { ConsoleDB } from '../plugins/codex-console/server/console-db.mjs';

const valid={exit_code:0,process_status:'exited',task_status:'completed',verification_status:'unknown',report:{status:'completed'}};
test('managed result refuses missing, failed, mismatched or timed-out results',()=>{
 assert.equal(classifyManagedResult(0,null).status,'failed');
 assert.equal(classifyManagedResult(7,valid).status,'failed');
 assert.equal(classifyManagedResult(0,{...valid,exit_code:7}).status,'failed');
 assert.equal(classifyManagedResult(0,{...valid,task_status:'partial'}).status,'failed');
 assert.equal(classifyManagedResult(0,valid,true).status,'failed');
 assert.equal(classifyManagedResult(0,valid).status,'succeeded');
 assert.equal(classifyManagedResult(0,{...valid,verification_status:'passed'}).verificationStatus,'unknown');
});
test('terminal operation cannot be overwritten by duplicate close event',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'d07-ops-'));
 const db=new ConsoleDB(root);
 try{
  const op=db.createOp({opType:'mock',prompt:'synthetic'});
  db.finishOp(op.id,{status:'failed',errorText:'startup'});
  db.finishOp(op.id,{status:'succeeded',outputText:'late'});
  assert.equal(db.getOp(op.id).status,'failed');
  assert.equal(db.getOp(op.id).errorText,'startup');
 }finally{db.db.close();fs.rmSync(root,{recursive:true,force:true});}
});
test('restart preserves non-success for orphaned running operation',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'d07-restart-'));
 let db=new ConsoleDB(root);
 try{
  const op=db.createOp({opType:'mock',prompt:'synthetic'});db.db.close();
  db=new ConsoleDB(root);
  assert.equal(db.getOp(op.id).status,'interrupted');
  db.finishOp(op.id,{status:'succeeded'});assert.equal(db.getOp(op.id).status,'interrupted');
 }finally{db.db.close();fs.rmSync(root,{recursive:true,force:true});}
});
test('spawn error yields exactly one callback',async()=>{
 const child=spawn(path.join(os.tmpdir(),'missing-d07-executable-999999'),[]);
 let calls=0;
 await new Promise(resolve=>watchOwnedChild(child,3000,()=>{calls++;resolve();},()=>{calls++;resolve();}));
 await new Promise(resolve=>setTimeout(resolve,50));
 assert.equal(calls,1);
});
