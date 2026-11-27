import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizePaired,quantiles,REPEATS,POLLS} from '../benchmarks/paired_display.mjs';
const identity={checkout:'a'.repeat(40),fixtureDigest:'b'.repeat(64)};
const rows=()=>Array.from({length:REPEATS},(_,pair)=>['baseline','candidate'].map(arm=>({
 pair,arm,status:'PASS',ms:pair+1,responseBytes:arm==='baseline'?1000:400,requestBytes:100,
 completed:POLLS,retries:0,semanticMatch:true}))).flat();
test('nearest-rank p95 and median with explicit count',()=>{
 assert.deepEqual(quantiles([6,1,5,2,4,3]),{medianMs:3.5,p95Ms:6});
 assert.equal(quantiles([]),null);assert.throws(()=>quantiles([NaN]));
});
test('paired denominator counts requests and responses, no fabricated tokens',()=>{
 const r=summarizePaired(rows(),identity);
 assert.equal(r.communication.baselineBytes,6600);assert.equal(r.communication.candidateBytes,3000);
 assert.equal(r.communication.savingPercent,54.545);assert.equal(r.communication.deviation,'WITHIN');
 assert.equal(r.groups.candidate.successRate,1);assert.equal(r.usage.combinedTokens,null);
 assert.equal(r.usage.codex.totalTokens,null);assert.equal(r.usage.gemini.estimatedTokens,null);
 assert.equal(r.quality.realTaskQuality,'NOT_RUN');assert.equal(r.formalAcceptance,'BLOCKED');
});
test('failures/unknown/not-run not dropped and prevent savings claim',()=>{
 for(const status of ['FAIL','UNKNOWN','NOT_RUN']){
   const x=rows();Object.assign(x[1],{status,completed:0,semanticMatch:false});
   const r=summarizePaired(x,identity);
   assert.equal(r.groups.candidate.passed,5);assert.equal(r.groups.candidate.attempted,6);
   assert.equal(r.communication.savingPercent,null);assert.equal(r.candidateCheck,'FAIL');
 }
});
test('missing duplicate or malformed samples fail closed',()=>{
 for(const x of [rows().slice(1),rows().map((r,i)=>i===1?{...r,arm:'baseline'}:r),
   rows().map((r,i)=>i===1?{...r,ms:Infinity}:r),rows().map((r,i)=>i===1?{...r,completed:1}:r)]){
   assert.throws(()=>summarizePaired(x,identity));
 }
});
test('above and below hypothesis reported, not coerced to PASS savings',()=>{
 for(const [bytes,deviation] of [[100,'ABOVE'],[1000,'BELOW']]){
   const r=summarizePaired(rows().map(x=>x.arm==='candidate'?{...x,responseBytes:bytes}:x),identity);
   assert.equal(r.communication.deviation,deviation);assert.equal(r.formalAcceptance,'BLOCKED');
 }
});
test('output whitelist drops prompt paths and model data',()=>{
 const r=summarizePaired(rows().map(x=>({...x,prompt:'PRIVATE_PROMPT',path:'PRIVATE_PATH'})),identity);
 assert.ok(!JSON.stringify(r).includes('PRIVATE_'));
});
