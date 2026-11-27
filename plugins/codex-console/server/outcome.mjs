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
