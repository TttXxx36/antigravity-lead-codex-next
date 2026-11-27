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

function fileStamp(file){
  try{
    const s=fs.lstatSync(file,{bigint:true});
    if(s.isSymbolicLink()||!s.isFile())throw Error('unsafe cache source');
    return [s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs].map(String);
  }catch(err){if(err.code==='ENOENT')return ['missing'];throw err;}
}

// SQLite WAL is part of the source identity. Never open or modify native DBs here.
// Unknown/unbounded marker metadata disables cache; periodic TTL bounds artifact lag.
export function displayStamp(dbPaths,dispatchDir){
  try{
    const files=[...dbPaths.flatMap(f=>[f,f+'-wal',f+'-journal']),path.join(dispatchDir,'state.json')];
    const marker=files.at(-1);
    const st=fs.lstatSync(marker);
    if(st.isSymbolicLink()||!st.isFile())return null;
    if(st.size<=4096){
      const value=JSON.parse(fs.readFileSync(marker,'utf8'));
      if(value.storage){
        if(value.storage!=='sqlite-v1'||!/^dispatch-state-[a-f0-9]{32}\.sqlite$/.test(value.database))return null;
        const f=path.join(dispatchDir,value.database);files.push(f,f+'-wal',f+'-journal');
      }
    } else {
      // Large JSON is valid legacy state, but do not parse it just to determine caching.
      // Bypass rather than risk missing a malformed/oversized SQLite marker.
      return null;
    }
    return JSON.stringify(files.map(fileStamp));
  }catch{return null;}
}

export function revisionEnvelope(value,revision){
  const stable={...value};delete stable.fetchedAt;
  const current=crypto.createHash('sha256').update(JSON.stringify(stable)).digest('hex');
  return current===revision?{revision:current,changed:false}:{revision:current,changed:true,value};
}
