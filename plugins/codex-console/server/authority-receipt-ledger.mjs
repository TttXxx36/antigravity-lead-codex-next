// D06 candidate: durable receipt replay evidence, not production authority.
// Only a trusted host may choose this dedicated directory, public key, context
// and clock. No dispatcher/MCP caller, native DB access, worker launch or
// permission decision is wired to this module.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {validateAuthorityReceipt} from './authority-receipt.mjs';

const APP_ID=0x414c4336;
const VERSION=1;
const MAX_ROWS=4096;
const FILE='authority-receipts-v1.sqlite';
const CREATE="CREATE TABLE consumed_receipts(nonce_sha256 TEXT PRIMARY KEY CHECK(length(nonce_sha256)=64),receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64),recorded_at INTEGER NOT NULL CHECK(recorded_at>=0)) STRICT, WITHOUT ROWID";
const require=(ok,msg)=>{if(!ok)throw new Error('D06 ledger: '+msg);};
const sha=x=>createHash('sha256').update(x).digest('hex');
const comparable=p=>process.platform==='win32'?p.toLowerCase():p;
function canonicalDirectory(p){
  require(typeof p==='string'&&path.isAbsolute(p),'absolute existing directory required');
  const resolved=path.resolve(p),st=fs.lstatSync(resolved),actual=fs.realpathSync(resolved);
  require(st.isDirectory()&&!st.isSymbolicLink()&&comparable(resolved)===comparable(actual),'linked or noncanonical directory');
  return actual;
}
function contains(parent,child){
  const rel=path.relative(comparable(parent),comparable(child));
  return rel===''||(!path.isAbsolute(rel)&&rel!=='..'&&!rel.startsWith('..'+path.sep));
}
function regular(file,allowMissing=false){
  try{
    const st=fs.lstatSync(file);
    require(st.isFile()&&!st.isSymbolicLink()&&st.nlink===1&&comparable(fs.realpathSync(file))===comparable(file),'unsafe ledger file or sidecar');
    return st;
  }catch(e){if(allowMissing&&e?.code==='ENOENT')return null;throw e;}
}
function existingHeader(file){
  const fd=fs.openSync(file,'r');
  try{
    const h=Buffer.alloc(100);
    require(fs.readSync(fd,h,0,h.length,0)===h.length&&h.subarray(0,16).equals(Buffer.from('SQLite format 3\0','ascii'))&&
      h.readUInt32BE(68)===APP_ID&&h.readUInt32BE(60)===VERSION,'unknown or incomplete ledger; no recovery overwrite');
  }finally{fs.closeSync(fd);}
}
function checkSidecars(file){
  require(!regular(file+'-wal',true)&&!regular(file+'-shm',true),'unexpected WAL sidecar');
  regular(file+'-journal',true);
}
function transaction(db,fn){
  db.exec('BEGIN IMMEDIATE');
  try{const value=fn();db.exec('COMMIT');return value;}
  catch(e){try{db.exec('ROLLBACK');}catch{}throw e;}
}
function checkSchema(db){
  require(db.prepare('PRAGMA application_id').get().application_id===APP_ID&&db.prepare('PRAGMA user_version').get().user_version===VERSION,'ledger version mismatch');
  const rows=db.prepare("SELECT type,name,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY name").all();
  require(rows.length===1&&rows[0].type==='table'&&rows[0].name==='consumed_receipts'&&rows[0].sql===CREATE,'ledger schema mismatch');
  const n=db.prepare('SELECT count(*) AS n FROM consumed_receipts').get().n;
  require(Number.isSafeInteger(n)&&n>=0&&n<=MAX_ROWS,'ledger capacity or integrity mismatch');
  return n;
}

export function openAuthorityReceiptLedger({directory,codexHome,dispatchStateDir,clock=()=>Math.floor(Date.now()/1000)}={}){
  require(typeof clock==='function','trusted clock required');
  const root=canonicalDirectory(directory),native=canonicalDirectory(codexHome),dispatch=canonicalDirectory(dispatchStateDir);
  for(const protectedRoot of [native,dispatch]){
    require(!contains(protectedRoot,root)&&!contains(root,protectedRoot),'ledger must be isolated from native and dispatcher storage');
  }
  const file=path.join(root,FILE);
  checkSidecars(file);
  let created=false;
  try{const fd=fs.openSync(file,'wx',0o600);created=true;fs.closeSync(fd);}
  catch(e){if(e?.code!=='EEXIST')throw e;}
  regular(file);
  if(!created)existingHeader(file);
  else require(!regular(file+'-journal',true),'unexpected journal for new ledger');
  const db=new DatabaseSync(file);
  let closed=false;
  try{
    db.exec('PRAGMA busy_timeout=3000; PRAGMA trusted_schema=OFF;');
    if(created){
      transaction(db,()=>{
        db.exec(CREATE+'; PRAGMA application_id='+APP_ID+'; PRAGMA user_version='+VERSION+';');
      });
    }
    require(db.prepare('PRAGMA journal_mode').get().journal_mode==='delete','unexpected ledger journal mode');
    checkSchema(db);
  }catch(e){db.close();throw e;}
  return Object.freeze({
    record(raw,{publicKey,expected}={}){
      require(!closed,'ledger closed');
      // BEGIN IMMEDIATE plus unique nonce digest gives a cross-connection
      // at-most-once evidence record. Signature/binding/expiry validated
      // while holding the write reservation. No external operation is run.
      return transaction(db,()=>{
        const n=checkSchema(db),now=clock();
        const receipt=validateAuthorityReceipt(raw,{publicKey,expected,now,seenNonces:new Set()});
        const nonceDigest=sha(receipt.nonceKey);
        require(!db.prepare('SELECT 1 FROM consumed_receipts WHERE nonce_sha256=?').get(nonceDigest),'receipt already recorded');
        require(n<MAX_ROWS,'ledger full; no automatic pruning');
        db.prepare('INSERT INTO consumed_receipts(nonce_sha256,receipt_sha256,recorded_at) VALUES(?,?,?)').run(nonceDigest,receipt.receiptSha256,now);
        return Object.freeze({receiptValid:true,receiptSha256:receipt.receiptSha256,nonceDigest,
          replayConsumption:'RECORDED_OFFLINE',executionAuthorized:false,mergeAuthorized:false});
      });
    },
    close(){if(!closed){db.close();closed=true;}}
  });
}
