// D06 offline receipt validation core. No production authority is provisioned.
// This module verifies a detached signed evidence envelope against a caller-
// pinned PUBLIC key. It never grants a permission, performs an operation,
// writes a nonce ledger, starts a model or enables a production route.
import {createHash,verify,KeyObject} from 'node:crypto';

const AUDIENCE='antigravity-lead-codex-next';
const ACTIONS=new Set(['network','worktree_cleanup','scheduler_reconcile','independent_acceptance','app_server_route']);
const DIGEST=/^[a-f0-9]{64}$/;
const ID=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/;
const NONCE=/^[a-f0-9]{32}$/;
const FIELDS=['action','audience','evidenceSha256','expiresAt','issuedAt','keyId','nonce','requestId','revision','scopeSha256','taskId','version'];
const BINDING=['action','evidenceSha256','requestId','revision','scopeSha256','taskId'];
const MAX_BYTES=4096;
const MAX_TTL=300;
const require=(ok,message)=>{if(!ok)throw new Error('D06: '+message);};
const exactKeys=(v,keys)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===keys.join(',');
const validId=x=>typeof x==='string'&&ID.test(x)&&!x.includes('..')&&!x.endsWith('.')&&!/\.lock$/i.test(x);
const validDigest=x=>typeof x==='string'&&DIGEST.test(x);
const safeInt=x=>Number.isSafeInteger(x)&&x>=0;

export function canonicalReceiptPayload(payload){
  require(exactKeys(payload,FIELDS),'invalid payload fields');
  require(payload.version===1&&payload.audience===AUDIENCE&&ACTIONS.has(payload.action),'invalid receipt action or audience');
  require(validId(payload.taskId)&&validId(payload.requestId)&&safeInt(payload.revision)&&payload.revision>0,'invalid task binding');
  require(validDigest(payload.keyId)&&validDigest(payload.scopeSha256)&&validDigest(payload.evidenceSha256)&&
          typeof payload.nonce==='string'&&NONCE.test(payload.nonce),'invalid digest or nonce');
  require(safeInt(payload.issuedAt)&&safeInt(payload.expiresAt)&&payload.expiresAt>payload.issuedAt&&
          payload.expiresAt-payload.issuedAt<=MAX_TTL,'invalid validity window');
  return Buffer.from(JSON.stringify(Object.fromEntries(FIELDS.map(k=>[k,payload[k]]))),'ascii');
}

export function publicKeyId(publicKey){
  require(publicKey instanceof KeyObject&&publicKey.type==='public'&&publicKey.asymmetricKeyType==='ed25519','pinned Ed25519 public key required');
  return createHash('sha256').update(publicKey.export({format:'der',type:'spki'})).digest('hex');
}

export function validateAuthorityReceipt(raw,{publicKey,expected,now,seenNonces}={}){
  require(typeof raw==='string'&&Buffer.byteLength(raw,'utf8')<=MAX_BYTES&&/^[\x20-\x7e]+$/.test(raw),'invalid bounded ASCII receipt');
  const keyId=publicKeyId(publicKey); // never take a trust key from the receipt
  require(exactKeys(expected,[...BINDING].sort())&&safeInt(now)&&seenNonces instanceof Set,'explicit trusted verification context required');
  let parsed;
  try{parsed=JSON.parse(raw);}catch{throw new Error('D06: malformed receipt');}
  require(exactKeys(parsed,['payload','signature']),'invalid envelope fields');
  const payload=parsed.payload, message=canonicalReceiptPayload(payload);
  require(typeof parsed.signature==='string'&&/^[A-Za-z0-9_-]{86}$/.test(parsed.signature),'invalid signature encoding');
  const sig=Buffer.from(parsed.signature,'base64url');
  require(sig.length===64&&sig.toString('base64url')===parsed.signature,'noncanonical signature');
  const canonical='{"payload":'+message.toString('ascii')+',"signature":'+JSON.stringify(parsed.signature)+'}';
  // Exact canonical bytes also reject duplicate JSON keys, escaped aliases,
  // whitespace variants and alternate number encodings.
  require(raw===canonical,'noncanonical receipt');
  require(payload.keyId===keyId,'untrusted issuer');
  require(BINDING.every(k=>payload[k]===expected[k]),'binding mismatch');
  require(payload.issuedAt<=now&&now<payload.expiresAt,'receipt outside validity window');
  require(!seenNonces.has(keyId+':'+payload.nonce),'receipt nonce already observed');
  require(verify(null,message,publicKey,sig),'signature mismatch');
  return Object.freeze({receiptValid:true,receiptSha256:createHash('sha256').update(raw,'ascii').digest('hex'),
    keyId,nonceKey:keyId+':'+payload.nonce,operation:payload.action,taskId:payload.taskId,revision:payload.revision,
    replayConsumption:'REQUIRES_TRUSTED_ATOMIC_LEDGER',executionAuthorized:false,mergeAuthorized:false});
}
