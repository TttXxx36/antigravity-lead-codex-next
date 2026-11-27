import { execFile } from 'node:child_process';
import path from 'node:path';

export function classifyManagedResult(code, parsed, timedOut = false) {
  const taskStatus = parsed?.task_status;
  const valid = parsed && typeof parsed === 'object' &&
    typeof parsed.exit_code === 'number' && parsed.report &&
    ['completed','partial','blocked','failed'].includes(taskStatus) &&
    parsed.report.status === taskStatus;
  const success = !timedOut && code === 0 && valid && parsed.exit_code === 0 &&
    parsed.process_status === 'exited' && taskStatus === 'completed';
  // Worker claims never become independent verification.
  return {status:success?'succeeded':'failed', taskStatus:valid?taskStatus:'unknown',
    processStatus:timedOut?'timed_out':code===0?'exited':'failed',
    verificationStatus:valid && ['unknown','not_run','failed'].includes(parsed.verification_status)
      ? parsed.verification_status : 'unknown',
    error:success?null:timedOut?'Worker timeout; termination requested':'Worker failed, incomplete or missing valid result'};
}


// The explicit v2 result is distinct from the legacy report object. A duplicate
// receipt is metadata, not a worker result or independent verification.
export function classifyKeyedResult(code, parsed, expectedTaskId, expectedRev, timedOut = false) {
  const taskStatus = parsed?.task_status;
  const ref = parsed?.result_ref;
  const expectedPrefix = 'runs/' + expectedTaskId + '/';
  const valid = parsed && parsed.version === 2 && parsed.task_id === expectedTaskId &&
    parsed.rev === expectedRev && parsed.base_rev === expectedRev - 1 &&
    Number.isInteger(parsed.exit_code) &&
    ['completed','partial','blocked','failed'].includes(taskStatus) &&
    ['exited','failed','launch_failed','timed_out'].includes(parsed.process_status) &&
    typeof ref === 'string' && ref.startsWith(expectedPrefix) &&
    /^runs\/[A-Za-z0-9._-]+\/(?:[A-Za-z0-9._-]+\/)?result\.json$/.test(ref) &&
    !ref.split('/').some(v=>v==='..'||v==='.') &&
    typeof parsed.summary === 'string' && typeof parsed.process_error === 'boolean';
  const success = !timedOut && code === 0 && valid && parsed.exit_code === 0 &&
    parsed.process_status === 'exited' && taskStatus === 'completed' && !parsed.process_error;
  return {status:success?'succeeded':'failed', taskStatus:valid?taskStatus:'unknown',
    processStatus:timedOut?'timed_out':code===0?'exited':'failed',
    verificationStatus:valid&&['unknown','not_run','failed'].includes(parsed.verification_status)
      ? parsed.verification_status:'unknown',
    error:success?null:timedOut?'Worker timeout; termination requested':'Keyed invocation incomplete, conflicting or missing valid v2 result'};
}

export function terminateOwnedChild(child) {
  if (!child?.pid) return;
  if (process.platform === 'win32') {
    if (child.exitCode !== null || child.signalCode !== null) return;
    const exe = path.join(process.env.SystemRoot || 'C:\\Windows','System32','taskkill.exe');
    execFile(exe,['/PID',String(child.pid),'/T','/F'],{timeout:10000,windowsHide:true},()=>{
      if (child.exitCode === null && child.signalCode === null) child.kill();
    });
  } else {
    try { process.kill(-child.pid,'SIGKILL'); } catch {}
  }
}

export function watchOwnedChild(child, timeoutMs, onError, onClose) {
  let done = false;
  let timedOut = false;
  let grace;
  const finish = (fn,...args) => {
    if (done) return;
    done = true;
    clearTimeout(timer);
    clearTimeout(grace);
    fn(...args);
  };
  const timer = setTimeout(()=>{
    timedOut=true;
    terminateOwnedChild(child);
    grace=setTimeout(()=>finish(onClose,null,true),15000);
  },timeoutMs);
  child.once('error',err=>finish(onError,err));
  child.once('close',code=>finish(onClose,code,timedOut));
}
