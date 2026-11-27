import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {generateKeyPairSync,sign,createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {canonicalReceiptPayload,publicKeyId} from '../plugins/codex-console/server/authority-receipt.mjs';
import {openAuthorityReceiptLedger} from '../plugins/codex-console/server/authority-receipt-ledger.mjs';

const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const base={version:1,audience:'antigravity-lead-codex-next',action:'independent_acceptance',taskId:'task-1',
  requestId:'req-1',revision:5,scopeSha256:'a'.repeat(64),evidenceSha256:'b'.repeat(64),
  keyId:publicKeyId(publicKey),nonce:'c'.repeat(32),issuedAt:1000,expiresAt:1060};
const binding=p=>Object.fromEntries(['action','evidenceSha256','requestId','revision','scopeSha256','taskId'].map(k=>[k,p[k]]));
const receipt=p=>{
  const bytes=canonicalReceiptPayload(p);
  return '{"payload":'+bytes.toString('ascii')+',"signature":'+JSON.stringify(sign(null,bytes,privateKey).toString('base64url'))+'}';
};
function fixture(t){
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'alc-receipt-')));
  const handles=[];
  t.after(()=>{for(const db of handles.reverse())db.close();fs.rmSync(root,{recursive:true,force:true});});
  const directories={directory:path.join(root,'ledger'),codexHome:path.join(root,'native'),dispatchStateDir:path.join(root,'dispatch')};
  for(const d of Object.values(directories))fs.mkdirSync(d);
  const sentinel=path.join(directories.codexHome,'native.sqlite');
  fs.writeFileSync(sentinel,'do not alter');
  const opts={...directories,clock:()=>1001};
  return {opts,directories,sentinel,handles,file:path.join(directories.directory,'authority-receipts-v1.sqlite')};
}
function open(f){const db=openAuthorityReceiptLedger(f.opts);f.handles.push(db);return db;}
const ctx={publicKey,expected:binding(base)};
function count(file){
  const db=new DatabaseSync(file,{readOnly:true});
  try{return db.prepare('SELECT count(*) AS n FROM consumed_receipts').get().n;}
  finally{db.close();}
}
test('durable replay evidence survives close/reopen and never grants execution',t=>{
  const f=fixture(t),raw=receipt(base),db=open(f),p=db.record(raw,ctx);
  assert.equal(p.replayConsumption,'RECORDED_OFFLINE');assert.equal(p.executionAuthorized,false);assert.equal(p.mergeAuthorized,false);
  assert.ok(Object.isFrozen(p));assert.equal(count(f.file),1);db.close();
  const second=open(f);
  assert.throws(()=>second.record(raw,ctx),/already recorded/);
  assert.equal(second.record(receipt({...base,nonce:'d'.repeat(32)}),ctx).receiptValid,true);
  assert.equal(count(f.file),2);second.close();
  const bytes=fs.readFileSync(f.file);
  assert.equal(bytes.includes(Buffer.from(raw)),false);assert.equal(bytes.includes(Buffer.from(base.taskId)),false);
  assert.equal(fs.readFileSync(f.sentinel,'utf8'),'do not alter');
});
test('invalid/expired/mismatched receipt leaves no nonce consumed',t=>{
  const f=fixture(t),db=open(f),raw=receipt(base),tampered=JSON.parse(raw);
  tampered.signature=(tampered.signature[0]==='A'?'B':'A')+tampered.signature.slice(1);
  assert.throws(()=>db.record(JSON.stringify(tampered),ctx),/signature mismatch/);
  assert.throws(()=>db.record(raw,{...ctx,expected:{...ctx.expected,revision:6}}),/binding mismatch/);
  assert.throws(()=>db.record(receipt({...base,issuedAt:900,expiresAt:1000}),ctx),/validity window/);
  assert.equal(count(f.file),0);
  assert.equal(db.record(raw,ctx).receiptValid,true);
  assert.equal(count(f.file),1);
});
test('native/dispatcher overlap, unknown files and unsafe directory refused',t=>{
  const f=fixture(t);
  for(const directory of [f.directories.codexHome,f.directories.dispatchStateDir,path.dirname(f.directories.directory)]){
    assert.throws(()=>openAuthorityReceiptLedger({...f.opts,directory}),/isolated/);
  }
  fs.writeFileSync(f.file,'unknown existing data');
  assert.throws(()=>openAuthorityReceiptLedger(f.opts),/unknown or incomplete ledger/);
  assert.equal(fs.readFileSync(f.file,'utf8'),'unknown existing data');
  assert.equal(fs.readFileSync(f.sentinel,'utf8'),'do not alter');
});
test('two independent processes can record a nonce at most once',async t=>{
  const f=fixture(t);open(f).close();
  const url=new URL('../plugins/codex-console/server/authority-receipt-ledger.mjs',import.meta.url).href;
  const program="import fs from 'node:fs';import {createPublicKey} from 'node:crypto';import {openAuthorityReceiptLedger} from "+JSON.stringify(url)+";const x=JSON.parse(fs.readFileSync(0,'utf8'));let db;try{db=openAuthorityReceiptLedger({...x.dirs,clock:()=>1001});db.record(x.raw,{publicKey:createPublicKey(x.pem),expected:x.expected});console.log('RECORDED')}catch(e){if(e.message.includes('already recorded'))console.log('REPLAY');else{console.error(e.message);process.exitCode=2}}finally{db?.close()}";
  const input=JSON.stringify({dirs:f.directories,raw:receipt(base),pem:publicKey.export({format:'pem',type:'spki'}),expected:ctx.expected});
  const run=()=>new Promise((resolve,reject)=>{
    const p=spawn(process.execPath,['--no-warnings','--input-type=module','-e',program],{stdio:['pipe','pipe','pipe']});
    let out='',err='';p.stdout.on('data',x=>out+=x);p.stderr.on('data',x=>err+=x);
    const timer=setTimeout(()=>{p.kill();reject(new Error('fixture process timeout'));},15000);
    p.once('error',e=>{clearTimeout(timer);reject(e);});
    p.once('close',code=>{clearTimeout(timer);if(code!==0)reject(new Error(err));else resolve(out.trim());});
    p.stdin.end(input);
  });
  assert.deepEqual((await Promise.all([run(),run()])).sort(),['RECORDED','REPLAY']);
  assert.equal(count(f.file),1);
});
test('bounded ledger fails closed without deleting replay history',t=>{
  const f=fixture(t);open(f).close();
  const db=new DatabaseSync(f.file);
  try{
    db.exec('BEGIN IMMEDIATE');
    const put=db.prepare('INSERT INTO consumed_receipts VALUES(?,?,?)');
    for(let i=0;i<4096;i++){
      const hash=createHash('sha256').update('fixture-'+i).digest('hex');put.run(hash,hash,1000);
    }
    db.exec('COMMIT');
  }finally{db.close();}
  const ledger=open(f);
  assert.throws(()=>ledger.record(receipt(base),ctx),/ledger full/);
  assert.equal(count(f.file),4096);
});
