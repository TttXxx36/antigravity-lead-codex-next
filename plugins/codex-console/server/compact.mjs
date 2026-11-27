import crypto from 'node:crypto';

function clip(v,n) {
  if (typeof v !== 'string') return null;
  return Array.from(v).slice(0,n).join('');
}
const status = v => typeof v === 'string' && /^[a-zA-Z0-9_-]{1,40}$/.test(v) ? v : 'unknown';
const num = v => Number.isSafeInteger(v) ? v : null;
const id = v => typeof v === 'string' && /^[A-Za-z0-9_.:-]{1,256}$/.test(v) ? v : null;
export function compactReply(value,budget=1500) {
  const text=JSON.stringify(value);
  if (Buffer.byteLength(text,'utf8')>budget) return {isError:true,content:[{type:'text',text:'{"error":"response budget exceeded; use UI for detail"}'}]};
  return {content:[{type:'text',text}]};
}
export function compactError() {
  return {isError:true,content:[{type:'text',text:'{"error":"record unavailable, ambiguous or invalid; check UI diagnostics"}'}]};
}
export function compactStatus(store,args,includeResult=false) {
  if (Boolean(args.threadId)===Boolean(args.taskId)) throw new Error('Select exactly one identifier');
  if (args.taskId) {
    const entry=store.getManagedTask(args.taskId,includeResult);
    if(!entry) throw new Error('Task not found');
    const {task,result}=entry;
    const out={taskId:id(task.task_id),threadId:id(task.session_id),status:status(task.status),exitCode:num(task.exit_code),verification:'unknown',...(task.protocol_version===2?{protocolVersion:2,rev:num(task.protocol_rev)}:{})};
    if(!includeResult) return out;
    // A report from a prior resume is not current terminal verification.
    const terminal=['completed','failed','partial','blocked','timed_out'].includes(task.status);
    return {...out,reportAvailable:terminal && !!result,summary:terminal?clip(result?.report?.summary ?? result?.summary,240):null,
      risks:terminal && Array.isArray(result?.report?.risks_or_followups)?result.report.risks_or_followups.slice(0,2).map(v=>clip(v,80)):[],
      reportTrust:'worker_claim',verification:'unknown',...(terminal && result?.report?.risks_or_followups?.length>2?{risksTruncated:true}:{})};
  }
  const t=store.getThread(args.threadId);
  if(!t) throw new Error('Thread not found');
  const out={threadId:id(t.id),taskId:id(t.dispatchTask?.taskId),status:status(t.status?.code),exitCode:num(t.dispatchTask?.exitCode),verification:'unknown'};
  if(!includeResult) return out;
  return {...out,summary:clip(t.latestReply,220),reportTrust:'thread_preview_not_current_result'};
}
export function compactDelta(store,args) {
  const value=compactStatus(store,args,true);
  const revision=crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
  return args.revision===revision?{revision,changed:false}:{revision,changed:true,result:value};
}
export function compactOperation(op) {
  if(!op) throw new Error('Operation not found');
  return {opId:id(op.id),threadId:id(op.threadId),status:status(op.status),durationMs:num(op.durationMs)};
}
