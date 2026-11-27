import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { performance } from 'node:perf_hooks';

// Display-only cache; authoritative task, execution and artifact checks bypass it.
export class QueryCache {
  constructor({ttlMs=5000,maxEntries=32,maxBytes=2*1024*1024,clock=()=>performance.now()}={}) {
    this.ttlMs=ttlMs; this.maxEntries=maxEntries; this.maxBytes=maxBytes; this.clock=clock;
    this.entries=new Map(); this.flights=new Map(); this.bytes=0;
  }
  async get(key,{stamp=()=>null,load,cacheable=()=>true,force=false}){
    const before=stamp();
    const hit=this.entries.get(key);
    if(!force&&before!==null&&hit?.stamp===before&&this.clock()<hit.expires){
      this.entries.delete(key);this.entries.set(key,hit);
      return JSON.parse(hit.json);
    }
    const flightKey=JSON.stringify([key,before,force]);
    if(before!==null&&this.flights.has(flightKey))return JSON.parse(await this.flights.get(flightKey));
    const run=Promise.resolve().then(load).then(value=>{
      const json=JSON.stringify(value), bytes=Buffer.byteLength(json);
      if(before!==null&&before===stamp()&&cacheable(value)&&bytes<=this.maxBytes){
        const old=this.entries.get(key);if(old){this.bytes-=old.bytes;this.entries.delete(key);}
        this.entries.set(key,{stamp:before,expires:this.clock()+this.ttlMs,json,bytes});this.bytes+=bytes;
        while(this.entries.size>this.maxEntries||this.bytes>this.maxBytes){
          const first=this.entries.keys().next().value;this.bytes-=this.entries.get(first).bytes;this.entries.delete(first);
        }
      } else {
        const old=this.entries.get(key);if(old){this.bytes-=old.bytes;this.entries.delete(key);}
      }
      return json;
    }).catch(err=>{const old=this.entries.get(key);if(old){this.bytes-=old.bytes;this.entries.delete(key);}throw err;});
    if(before!==null&&this.flights.size<this.maxEntries)this.flights.set(flightKey,run);
    try{return JSON.parse(await run);}finally{if(this.flights.get(flightKey)===run)this.flights.delete(flightKey);}
  }
}

export function fileStamp(file){
  try{
    const s=fs.lstatSync(file,{bigint:true});
    if(s.isSymbolicLink()||!s.isFile())throw Error('unsafe cache source');
    return [s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs].map(String);
  }catch(err){if(err.code==='ENOENT')return ['missing'];throw err;}
}

// SQLite WAL is part of the source identity. Never open or modify native DBs here.
// Unknown/unbounded marker metadata disables cache; periodic TTL bounds artifact lag.
export function displayStamp(dbPaths,dispatchDir,memo=null,metrics=null){
  try{
    const files=[...dbPaths.flatMap(f=>[f,f+'-wal',f+'-journal']),path.join(dispatchDir,'state.json')];
    const marker=files.at(-1);
    const identity=fileStamp(marker),key=JSON.stringify(identity);
    if(identity[0]!=='missing'&&BigInt(identity[2])<=4096n){
      let value;
      if(memo?.key===key)value=memo.value;
      else{
        const fd=fs.openSync(marker,'r');
        let raw;
        try{
          const buf=Buffer.alloc(4097);let n=0;
          while(n<buf.length){const m=fs.readSync(fd,buf,n,buf.length-n,null);if(!m)break;n+=m;}
          raw=buf.subarray(0,n);
        }finally{fs.closeSync(fd);}
        if(metrics){metrics.fileReads++;metrics.fileBytes+=raw.length;}
        if(raw.length>4096||JSON.stringify(fileStamp(marker))!==key)return null;
        value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
        if(memo){memo.key=key;memo.value=value;}
      }
      if(!value||typeof value!=='object'||Array.isArray(value))return null;
      if(Object.hasOwn(value,'storage')){
        if(value.storage!=='sqlite-v1'||!/^dispatch-state-[a-f0-9]{32}\.sqlite$/.test(value.database))return null;
        const f=path.join(dispatchDir,value.database);files.push(f,f+'-wal',f+'-journal');
      }
    }
    // Large valid legacy JSON has no valid D15 marker; authoritative loader
    // checks it. No repeated parse on hit. Check marker identity again.
    const stamps=files.map(fileStamp);
    if(JSON.stringify(stamps[dbPaths.length*3])!==key)return null;
    return JSON.stringify(stamps);
  }catch{return null;}
}
export function createDisplayStamp(dbPaths,dispatchDir,metrics=null){
  const memo={key:null,value:null};
  return ()=>displayStamp(dbPaths,dispatchDir,memo,metrics);
}

export function revisionEnvelope(value,revision){
  const stable={...value};delete stable.fetchedAt;
  const current=crypto.createHash('sha256').update(JSON.stringify(stable)).digest('hex');
  return current===revision?{revision:current,changed:false}:{revision:current,changed:true,value};
}


// Per-artifact cache for display only. Metadata stamps are checked on every
// use; bounded read + canonical path + no symlink. No model-facing proof is cached.
export class DisplayReportCache {
  constructor(root,{maxEntries=128,maxBytes=2*1024*1024}={}){
    this.root=path.resolve(root);this.maxEntries=maxEntries;this.maxBytes=maxBytes;
    this.entries=new Map();this.bytes=0;this.reads=0;this.readBytes=0;
  }
  read(task){
    try{
      const id=task?.task_id;
      if(typeof id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(id)||id.includes('..')||id.endsWith('.')||/\.lock$/i.test(id))return null;
      const dir=path.join(this.root,'runs',id);
      const canonical=path.join(fs.realpathSync(this.root),'runs',id);
      if(path.resolve(task.run_dir)!==dir||fs.realpathSync(dir)!==canonical||fs.lstatSync(dir).isSymbolicLink())return null;
      // Current published turn takes precedence. Legacy records have no ref.
      let files;
      if(task.result_ref){
        const turn=task.result_ref.turn;
        if(task.active_turn_id||!['completed','failed','partial','blocked','timed_out'].includes(task.status)||
           !(turn===null||(typeof turn==='string'&&/^turn-[A-Za-z0-9_-]+$/.test(turn)))||!/^[a-f0-9]{64}$/.test(task.result_ref.sha256))return null;
        files=[path.join(dir,...(turn===null?[]:[turn]),'result.json')];
      }else{
        if(task.active_turn_id||['reserved','running','interrupted'].includes(task.status))return null;
        files=fs.readdirSync(dir,{withFileTypes:true}).filter(x=>x.isDirectory()&&/^turn-[A-Za-z0-9_-]+$/.test(x.name))
          .map(x=>path.join(dir,x.name,'result.json')).sort().reverse();
        files.push(path.join(dir,'result.json'));
      }
      for(const file of files){
        let st;
        try{st=fs.lstatSync(file,{bigint:true});}catch(err){if(err.code==='ENOENT')continue;throw err;}
        if(!st.isFile()||st.isSymbolicLink()||st.size>262144n||
          fs.realpathSync(file)!==path.join(canonical,path.relative(dir,file)))return null;
        const identity=[id,task.status,task.session_id??null,task.exit_code??null,task.task_status??null,task.result_ref?.turn??null,task.result_ref?.sha256??null];
        const stamp=JSON.stringify([fileStamp(file),identity]);
        let entry=this.entries.get(file);
        if(entry?.stamp===stamp){this.entries.delete(file);this.entries.set(file,entry);return JSON.parse(entry.json);}
        const fd=fs.openSync(file,'r');
        let raw;
        try{
          const buf=Buffer.alloc(262145);let n=0;
          while(n<buf.length){const m=fs.readSync(fd,buf,n,buf.length-n,null);if(!m)break;n+=m;}
          raw=buf.subarray(0,n);this.reads++;this.readBytes+=n;
        }finally{fs.closeSync(fd);}
        if(raw.length>262144||JSON.stringify([fileStamp(file),identity])!==stamp)return null;
        if(task.result_ref&&crypto.createHash('sha256').update(raw).digest('hex')!==task.result_ref.sha256)return null;
        const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
        if(!value||typeof value!=='object'||Array.isArray(value))return null;
        if(task.result_ref&&(value.task_id!==id||(value.turn_id??null)!==task.result_ref.turn||
          value.session_id!==task.session_id||value.exit_code!==task.exit_code||value.task_status!==task.task_status||
          value.report?.status!==value.task_status))return null;
        const json=JSON.stringify(value),bytes=Buffer.byteLength(json);
        if(entry){this.bytes-=entry.bytes;this.entries.delete(file);}
        if(bytes<=this.maxBytes){
          this.entries.set(file,{stamp,json,bytes});this.bytes+=bytes;
          while(this.entries.size>this.maxEntries||this.bytes>this.maxBytes){
            const first=this.entries.keys().next().value;this.bytes-=this.entries.get(first).bytes;this.entries.delete(first);
          }
        }
        return value;
      }
      return null;
    }catch{return null;}
  }
}
