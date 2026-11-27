import path from 'node:path';

// Git porcelain v1 -z returns destination then origin for renames/copies.
export function parsePorcelainZ(output,cwd) {
  if (!output) return [];
  if (!output.endsWith('\0')) throw new Error('Truncated git porcelain output');
  const fields=output.slice(0,-1).split('\0');
  const result=[];
  for(let i=0;i<fields.length;i++){
    const entry=fields[i];
    if(entry.length<4 || entry[2]!==' ')throw new Error('Malformed git status entry');
    const xy=entry.slice(0,2);
    const file=entry.slice(3);
    const row={xy:xy.trim(),file,absPath:path.join(cwd,file)};
    if(/[RC]/.test(xy)){
      const origin=fields[++i];
      if(!origin)throw new Error('Missing rename source');
      row.originalFile=origin;
    }
    result.push(row);
  }
  return result;
}
