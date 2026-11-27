import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {canonicalReceiptPayload,publicKeyId,validateAuthorityReceipt} from '../plugins/codex-console/server/authority-receipt.mjs';

const {publicKey,privateKey}=generateKeyPairSync('ed25519');
const base={version:1,audience:'antigravity-lead-codex-next',action:'independent_acceptance',taskId:'task-1',
  requestId:'req-1',revision:5,scopeSha256:'a'.repeat(64),evidenceSha256:'b'.repeat(64),
  keyId:publicKeyId(publicKey),nonce:'c'.repeat(32),issuedAt:1000,expiresAt:1060};
const binding=p=>Object.fromEntries(['action','evidenceSha256','requestId','revision','scopeSha256','taskId'].map(k=>[k,p[k]]));
const receipt=p=>{
  const bytes=canonicalReceiptPayload(p),sig=sign(null,bytes,privateKey).toString('base64url');
  return '{"payload":'+bytes.toString('ascii')+',"signature":'+JSON.stringify(sig)+'}';
};
const verify=(raw,opts={})=>validateAuthorityReceipt(raw,{publicKey,expected:binding(base),now:1001,seenNonces:new Set(),...opts});

test('valid signed fixture is evidence only, never execution authority',()=>{
  const seen=new Set(),p=verify(receipt(base),{seenNonces:seen});
  assert.equal(p.receiptValid,true);assert.equal(p.executionAuthorized,false);assert.equal(p.mergeAuthorized,false);
  assert.equal(p.replayConsumption,'REQUIRES_TRUSTED_ATOMIC_LEDGER');assert.equal(seen.size,0);
  assert.equal(p.receiptSha256.length,64);assert.ok(Object.isFrozen(p));
});
test('all five actions bind to exact external context',()=>{
  for(const action of ['network','worktree_cleanup','scheduler_reconcile','independent_acceptance','app_server_route']){
    const p={...base,action};
    assert.equal(verify(receipt(p),{expected:binding(p)}).executionAuthorized,false);
    if(action!==base.action)assert.throws(()=>verify(receipt(p)),/binding mismatch/);
  }
});
test('signature tamper and wrong pinned issuer reject',()=>{
  const raw=receipt(base),p=JSON.parse(raw);
  p.signature=(p.signature[0]==='A'?'B':'A')+p.signature.slice(1);
  assert.throws(()=>verify(JSON.stringify(p)),/signature mismatch/);
  const other=generateKeyPairSync('ed25519').publicKey;
  assert.throws(()=>verify(raw,{publicKey:other}),/untrusted issuer/);
  assert.throws(()=>verify(raw,{publicKey:undefined}),/pinned Ed25519/);
});
test('scope request revision and result hash cannot drift',()=>{
  for(const [k,value] of [['scopeSha256','d'.repeat(64)],['evidenceSha256','e'.repeat(64)],['taskId','other'],['requestId','other'],['revision',6]]){
    assert.throws(()=>verify(receipt({...base,[k]:value})),/binding mismatch/);
  }
});
test('expiry future and excessive duration reject',()=>{
  const raw=receipt(base);
  for(const now of [999,1060,2000])assert.throws(()=>verify(raw,{now}),/validity window/);
  assert.throws(()=>receipt({...base,expiresAt:1301}),/validity window/);
});
test('observed nonce is refused; validator never consumes it',()=>{
  const raw=receipt(base),p=verify(raw),seen=new Set([p.nonceKey]);
  assert.throws(()=>verify(raw,{seenNonces:seen}),/already observed/);
  assert.equal(seen.size,1);
});
test('noncanonical duplicate fields and unknown keys reject',()=>{
  const raw=receipt(base);
  for(const bad of [' '+raw,raw.replace('"version":1','"version":1,"version":1'),
                    raw.replace('"version":1','"version":1.0'),raw.replace('"taskId":"task-1"','"taskId":"task-1","extra":true')]){
    assert.throws(()=>verify(bad));
  }
  assert.throws(()=>verify(raw,{expected:{...binding(base),extra:true}}),/verification context/);
});
test('no private key, unknown action, external key injection or malformed data accepted',()=>{
  assert.throws(()=>verify(receipt(base),{publicKey:privateKey}),/pinned Ed25519/);
  assert.throws(()=>receipt({...base,action:'arbitrary'}),/action/);
  assert.throws(()=>receipt({...base,audience:'other'}),/audience/);
  assert.throws(()=>verify('x'.repeat(4097)),/bounded ASCII/);
  assert.throws(()=>verify(receipt(base),{seenNonces:undefined}),/verification context/);
  assert.throws(()=>verify(receipt(base),{now:NaN}),/verification context/);
});
