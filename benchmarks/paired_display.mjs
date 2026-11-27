// D21: fixed, bounded paired display workload. No model or provider access.
// Only numeric measurements and fixed enum/identity fields are reported.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';

export const REPEATS=6;
export const POLLS=5;
export const BASE_REF='505f5bf955f47b66c935b3371e3991085221e083';
const SHA=/^[0-9a-f]{40}$/;
const FLAGS=['baseline','candidate'];
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const count=x=>Number.isSafeInteger(x)&&x>=0;
const round=x=>Number(x.toFixed(3));
export function quantiles(xs){
  if(!xs.length)return null;
  if(xs.some(x=>!finite(x)))throw Error('invalid numeric measurement');
  const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);
  return {medianMs:round(a.length%2?a[m]:(a[m-1]+a[m])/2),p95Ms:round(a[Math.ceil(.95*a.length)-1])};
}
export function summarizePaired(rows,{checkout,fixtureDigest}){
  if(!SHA.test(checkout)||!/^[0-9a-f]{64}$/.test(fixtureDigest)||!Array.isArray(rows)||rows.length!==REPEATS*2)throw Error('invalid paired evidence identity/count');
  const seen=new Set();
  for(const r of rows){
    if(!r||!FLAGS.includes(r.arm)||!Number.isInteger(r.pair)||r.pair<0||r.pair>=REPEATS||seen.has(r.pair+':'+r.arm)||
       !['PASS','FAIL','UNKNOWN','NOT_RUN'].includes(r.status)||!finite(r.ms)||!count(r.responseBytes)||!count(r.requestBytes)||
       !count(r.completed)||r.completed>POLLS||r.retries!==0||typeof r.semanticMatch!=='boolean'||
       (r.status==='PASS'&&(r.completed!==POLLS||!r.semanticMatch)))throw Error('invalid paired row');
    seen.add(r.pair+':'+r.arm);
  }
  const groups=Object.fromEntries(FLAGS.map(arm=>{
    const all=rows.filter(r=>r.arm===arm),ok=all.filter(r=>r.status==='PASS');
    return [arm,{attempted:all.length,passed:ok.length,failed:all.filter(r=>r.status==='FAIL').length,
      unknown:all.filter(r=>r.status==='UNKNOWN').length,notRun:all.filter(r=>r.status==='NOT_RUN').length,
      successRate:ok.length/all.length,retries:all.reduce((s,r)=>s+r.retries,0),completedPolls:all.reduce((s,r)=>s+r.completed,0),
      timing:quantiles(ok.map(r=>r.ms)),requestBytes:all.reduce((s,r)=>s+r.requestBytes,0),
      responseBytes:all.reduce((s,r)=>s+r.responseBytes,0)}];
  }));
  const complete=FLAGS.every(k=>groups[k].passed===REPEATS);
  const denominator=groups.baseline.requestBytes+groups.baseline.responseBytes;
  const candidate=groups.candidate.requestBytes+groups.candidate.responseBytes;
  const saving=complete&&denominator>0?round(100*(denominator-candidate)/denominator):null;
  return {schemaVersion:1,mode:'same_checkout_feature_comparison',checkout,referenceCommit:BASE_REF,fixtureDigest,
    workload:'synthetic_console_snapshot_5_polls',repeats:REPEATS,pollsPerPair:POLLS,
    cache:'new_revision_force_first_then_reuse; OS_cache_uncontrolled',model:null,effort:null,
    baselineMode:'legacy_full_snapshot',candidateMode:'revision_delta',
    environment:{os:process.platform,arch:process.arch,node:process.version},
    groups,pairedSamples:rows.map(r=>({pair:r.pair,arm:r.arm,status:r.status,ms:round(r.ms),requestBytes:r.requestBytes,
      responseBytes:r.responseBytes,completed:r.completed,retries:r.retries,semanticMatch:r.semanticMatch})),
    communication:{unit:'serialized_JSON_RPC_request_plus_response_bytes_excluding_newline',baselineBytes:denominator,
      candidateBytes:candidate,savingPercent:saving,hypothesisPercent:[30,60],
      deviation:saving===null?'UNKNOWN':saving<30?'BELOW':saving>60?'ABOVE':'WITHIN'},
    quality:{fixtureEquivalence:complete?'PASS':'FAIL',p0FixtureRegressions:complete?0:null,realTaskQuality:'NOT_RUN',
      realTaskSuccess:'NOT_RUN',acceptance:'BLOCKED'},
    usage:{realModelCalls:0,codex:{source:'NOT_RUN',inputTokens:null,outputTokens:null,totalTokens:null},
      gemini:{source:'UNKNOWN',measuredTokens:null,estimatedTokens:null},combinedTokens:null,tokenSavingPercent:null},
    candidateCheck:complete?'PASS':'FAIL',formalAcceptance:'BLOCKED'};
}

export async function pairedDisplayBenchmark({rpc,root,expected,limit=50}){
  const checkout=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',timeout:5000}).trim();
  assert.match(checkout,SHA);
  // Both arms execute the exact same checked-out product source. Reference
  // is ancestry provenance, not a claim that old main was executed.
  execFileSync('git',['merge-base','--is-ancestor',BASE_REF,checkout],{cwd:root,timeout:5000});
  const normalize=value=>{
    assert.ok(value?.connected);assert.ok(!value.health?.errors?.length);assert.ok(Array.isArray(value.tasks));
    return {tasks:value.tasks.map(t=>[t.id,t.status.code,t.title]),
      managed:value.managedAgents.map(t=>[t.id,t.status]),stats:value.stats};
  };
  const expectedNorm=normalize(expected);
  const fixtureDigest=crypto.createHash('sha256').update(JSON.stringify({workload:'snapshot',limit,polls:POLLS,
    expectedTaskCount:expectedNorm.tasks.length,managedCount:expectedNorm.managed.length})).digest('hex');
  const rows=[];
  for(let pair=0;pair<REPEATS;pair++){
    for(const arm of pair%2?['candidate','baseline']:['baseline','candidate']){
      const row={pair,arm,status:'PASS',ms:0,requestBytes:0,responseBytes:0,completed:0,retries:0,semanticMatch:true};
      let revision,previous;
      const start=performance.now();
      try{
        for(let i=0;i<POLLS;i++){
          const args=arm==='baseline'?{limit}:{limit,...(i===0?{force:true}:{revision})};
          const name=arm==='baseline'?'console_snapshot':'console_snapshot_delta';
          const response=await rpc('tools/call',{name,arguments:args});
          assert.ok(Number.isSafeInteger(response.id));
          // Exact serialized envelope size, not socket or transport framing.
          row.requestBytes+=Buffer.byteLength(JSON.stringify({jsonrpc:'2.0',id:response.id,method:'tools/call',params:{name,arguments:args}}));
          row.responseBytes+=Buffer.byteLength(JSON.stringify(response));
          assert.ok(response.result&&!response.result.isError);
          const data=response.result.structuredContent;
          if(arm==='baseline')previous=data;
          else{
            assert.match(data.revision,/^[a-f0-9]{64}$/);
            if(i===0)assert.equal(data.changed,true);
            if(data.changed)previous=data.value;
            else {assert.equal(data.value,undefined);assert.equal(data.revision,revision);}
            revision=data.revision;
          }
          assert.deepEqual(normalize(previous),expectedNorm);
          row.completed++;
        }
      }catch(_){row.status='FAIL';row.semanticMatch=false;}
      row.ms=performance.now()-start;rows.push(row);
    }
  }
  const report=summarizePaired(rows,{checkout,fixtureDigest});
  console.log('D21_BENCH '+JSON.stringify(report));
  assert.equal(report.candidateCheck,'PASS','D21 paired fixture equivalence failed (redacted)');
  return report;
}
