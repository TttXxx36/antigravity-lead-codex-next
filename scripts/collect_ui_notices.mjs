// Collect exact notices for rendered modules in the tracked single-file UI.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const root=fileURLToPath(new URL('../plugins/codex-console/',import.meta.url));
const out=fileURLToPath(new URL('../dependency-audit/',import.meta.url));
const require=createRequire(path.join(root,'package.json'));
const {build}=require('vite');
const hash=b=>createHash('sha256').update(b).digest('hex');
const lockBytes=fs.readFileSync(path.join(root,'package-lock.json'));
const lock=JSON.parse(lockBytes).packages;
const inventory=JSON.parse(fs.readFileSync(path.join(out,'build.json'),'utf8'));
assert.equal(inventory.identityChecks,'PASS');
assert.equal(inventory.lockSha256,hash(lockBytes));
const installed=new Map(inventory.entries.map(e=>[e.package,e]));
const keys=Object.keys(lock).filter(Boolean).sort((a,b)=>b.length-a.length);
const packages=new Set(['node_modules/vite','node_modules/rollup']);
let virtual=0, chunks=0, projectModules=0;
const plugin={
  name:'alc-ui-notice-evidence',
  enforce:'pre',
  generateBundle:{
    order:'pre',
    handler(_options,bundle) {
      for(const c of Object.values(bundle)) {
        if(c.type!=='chunk')continue;
        chunks++;
        for(const raw of Object.keys(c.modules)) {
          const id=raw.replace(/^\0/,'').split('?')[0];
          if(!path.isAbsolute(id)){virtual++;continue;}
          const rel=path.relative(root,id).split(path.sep).join('/');
          assert.ok(!rel.startsWith('../')&&!path.isAbsolute(rel),'external module path');
          if(!rel.startsWith('node_modules/')){projectModules++;continue;}
          const found=keys.find(k=>rel.startsWith(k+'/'));
          assert.ok(found,'module absent from lock');
          packages.add(found);
        }
      }
    }
  }
};
process.chdir(root);
const built=await build({configFile:path.join(root,'vite.config.mjs'),plugins:[plugin],build:{write:false}});
const outputs=(Array.isArray(built)?built:[built]).flatMap(x=>x.output||[]);
const html=outputs.find(x=>x.type==='asset'&&x.fileName==='app.html');
assert.ok(chunks>0&&projectModules>0&&packages.size>=4&&html,'module observation incomplete');
assert.equal(hash(Buffer.from(html.source)),hash(fs.readFileSync(path.join(root,'dist/app.html'))),'notice build differs from tracked UI');
const list=[], blocks=[Buffer.from('# Third-party notices for the bundled Codex Console UI\n\nGenerated from the locked Linux build module inventory. Includes Vite and Rollup conservatively for generated helpers; this does not redistribute their native build binaries. Original notice bytes follow each heading. Other installed runtime packages retain their own notices. Do not remove this file when distributing dist/app.html.\n\n')];
for(const pkg of [...packages].sort()) {
  const e=installed.get(pkg);
  assert.ok(e&&e.version===lock[pkg].version&&e.notices.length>0,'missing module notice');
  const item={package:pkg,version:e.version,notices:[]};
  for(const n of [...e.notices].sort((a,b)=>a.name.localeCompare(b.name,'en'))) {
    assert.match(n.name,/^[A-Za-z0-9_.-]+$/);
    const f=path.join(root,pkg,n.name);
    assert.ok(fs.lstatSync(f).isFile()&&!fs.lstatSync(f).isSymbolicLink());
    const bytes=fs.readFileSync(f);
    assert.equal(hash(bytes),n.sha256);
    assert.equal(bytes.length,n.bytes);
    new TextDecoder('utf-8',{fatal:true}).decode(bytes);
    blocks.push(Buffer.from('## '+pkg.replace(/^node_modules\//,'')+'@'+e.version+' — '+n.name+'\n\nSHA256: '+n.sha256+'\n\n'),bytes,Buffer.from('\n\n---\n\n'));
    item.notices.push(n);
  }
  list.push(item);
}
const notice=Buffer.concat(blocks);
assert.ok(notice.length<=256*1024);
const report={uiSha256:hash(Buffer.from(html.source)),lockSha256:hash(lockBytes),noticeSha256:hash(notice),noticeBytes:notice.length,packages:list,virtualModuleCount:virtual,renderedChunkCount:chunks,projectModuleCount:projectModules};
fs.writeFileSync(path.join(out,'UI-THIRD-PARTY-NOTICES.md'),notice,{flag:'wx'});
fs.writeFileSync(path.join(out,'ui-notice-report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log('D22_UI_NOTICE_REPORT '+JSON.stringify(report));
if(process.argv.includes('--bootstrap')){
  // One-time transfer of audited public license bytes, not private data.
  const b64=notice.toString('base64');
  for(let i=0;i<b64.length;i+=4096)console.log('D22_UI_NOTICE_CHUNK '+(i/4096)+' '+b64.slice(i,i+4096));
}else{
  assert.ok(notice.equals(fs.readFileSync(path.join(root,'UI-THIRD-PARTY-NOTICES.md'))),'tracked UI notices are stale');
}
