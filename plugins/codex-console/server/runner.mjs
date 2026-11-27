import { execFile, spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';
import { classifyManagedResult, classifyKeyedResult, watchOwnedChild } from './outcome.mjs';
import { parsePorcelainZ } from './git-status.mjs';
import { runtimePaths, resolveExecutable, buildRuntimeEnv, normalizePath } from './platform.mjs';

const execFileAsync = promisify(execFile);

const DISPATCH_SCRIPT = path.join(runtimePaths().geminiConfigDir, 'skills', 'multi-agent-dispatch', 'scripts', 'dispatch.py');

export const DIAGNOSE_BLOCKER_PROMPT =
  '请基于当前完整上下文和 Goal 目标，用 3~5 条要点精炼说明：' +
  '1) 当前明确卡点或阻塞原因是什么；' +
  '2) 已完成和未完成的关键项分别是什么；' +
  '3) 需要用户或主控做出的下一步最小决策/动作是什么。' +
  '请严格保持只读，不要修改任何文件或执行写操作。';

export function resolveCodexBin() { return resolveExecutable('codex'); }
export function resolvePythonBin() { return resolveExecutable('python'); }
export function buildExecEnv() { return buildRuntimeEnv(); }

function safeCwd(cwd) {
  const resolved = normalizePath(cwd || os.homedir());
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    throw new Error('Invalid working directory: ' + resolved);
  }
  return resolved;
}


function keyedEnvelope(prompt, taskId, initial) {
  if (typeof taskId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(taskId)) {
    throw new Error('D13: explicit managed task ID required');
  }
  if (Buffer.byteLength(prompt,'utf8') > 8192) throw new Error('D13: envelope too large');
  let env;
  try { env=JSON.parse(prompt); } catch { throw new Error('D13: v2 JSON envelope required'); }
  if (!env || env.version!==2 || env.task_id!==taskId || !Number.isInteger(env.rev) ||
      !Number.isInteger(env.base_rev) || env.base_rev<0 || env.rev!==env.base_rev+1 ||
      env.rev>2147483647 || (initial?env.base_rev!==0:env.base_rev===0)) {
    throw new Error('D13: incompatible task identity/revision');
  }
  // Python is the authoritative strict schema/session/budget validator.
  return env.rev;
}
function requestOp(db, requestId, identity, options) {
  if (requestId == null) return {created:true,op:db.createOp(options)};
  const reservation=db.reserveRequest({requestId,identity,...options});
  if (reservation.conflict) throw new Error('D13: request ID conflict; original operation '+reservation.op.id+' ('+reservation.op.status+')');
  return reservation;
}

export class CodexRunner {
  constructor(consoleDb) {
    this.consoleDb = consoleDb;
    this.codexBin = resolveCodexBin();
    this.pythonBin = resolvePythonBin();
    this.gitBin = resolveExecutable('git');
  }

  getRuntimeInfo() {
    return {
      codexBin: this.codexBin,
      pythonBin: this.pythonBin,
      gitBin: this.gitBin,
      runtimeErrors: [['Codex', this.codexBin], ['Python', this.pythonBin], ['Git', this.gitBin]].filter(([, bin]) => !bin).map(([name]) => name + ' executable not found or invalid override'),
      dispatchAvailable: fs.existsSync(DISPATCH_SCRIPT),
      dispatchScript: DISPATCH_SCRIPT,
    };
  }

  /**
   * Non-destructive read-only question / blocker diagnosis via `codex exec fork --ephemeral`
   */
  startReadonlyAsk({ threadId, prompt, cwd, opType = 'readonly_ask' }) {
    if (!this.codexBin) throw new Error('Codex executable not found; set CODEX_BIN to a native executable');
    const actualPrompt = (prompt || '').trim() || DIAGNOSE_BLOCKER_PROMPT;
    const op = this.consoleDb.createOp({
      threadId,
      opType,
      prompt: actualPrompt,
      mode: 'fork_readonly',
      meta: { cwd: safeCwd(cwd) },
    });

    const outFile = path.join(os.tmpdir(), `codex-console-${op.id}.txt`);
    const args = [
      'exec',
      'fork',
      '--ephemeral',
      '--skip-git-repo-check',
      '-c',
      'sandbox_mode="read-only"',
      '-c',
      'sandbox_workspace_write.network_access=false',
      '-c',
      'approval_policy="never"',
      '-o',
      outFile,
      threadId,
      actualPrompt,
    ];

    const child = spawn(this.codexBin, args, {
      cwd: safeCwd(cwd),
      env: buildExecEnv(),
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      if (stdout.length < 200_000) stdout += chunk.toString('utf8');
    });
    child.stderr.on('data', (chunk) => {
      if (stderr.length < 80_000) stderr += chunk.toString('utf8');
    });

    watchOwnedChild(child, 180_000, (err) => {
      this.consoleDb.finishOp(op.id, {status:'failed',errorText:'启动 codex 失败: '+err.message});
    }, (code, timedOut) => {
      let finalMsg = '';
      if (fs.existsSync(outFile)) {
        try {
          finalMsg = fs.readFileSync(outFile, 'utf8').trim();
          fs.unlinkSync(outFile);
        } catch {
          // ignore
        }
      }
      const outputText = finalMsg || stdout.trim();
      if (!timedOut && code === 0 && outputText) {
        this.consoleDb.finishOp(op.id, {
          status: 'succeeded',
          outputText,
          errorText: stderr.trim() || null,
          metaPatch: { exitCode: code },
        });
      } else {
        this.consoleDb.finishOp(op.id, {
          status: 'failed',
          outputText: outputText || '',
          errorText:
            stderr.trim() ||
            (timedOut ? '只读诊断超时' : code !== 0 ? `codex exec fork 退出码 ${code}` : '未返回正文内容'),
          metaPatch: { exitCode: code },
        });
      }
    });

    return op;
  }

  /**
   * Send a message to an existing Codex thread:
   * - mode='queue': `codex queue --thread <id> --message <msg> --resume` (fast sync)
   * - mode='resume': `codex exec resume <id> <msg>` (background async)
   * - mode='dispatch_resume': `dispatch.py resume --task-id <taskId> --prompt <msg>` (background async)
   */
  async sendMessage({
    threadId,
    message,
    mode = 'queue',
    cwd = null,
    allowDuplicate = false,
    taskId = null,
    requestId = null,
    retryOf = null,
  }) {
    const cleanMsg = (message || '').trim();
    if (!cleanMsg) {
      throw new Error('消息内容不能为空');
    }

    if (!['readonly', 'dispatch_resume'].includes(mode)) {
      throw new Error('D06: unmanaged queue/resume denied; use managed dispatch_resume or readonly');
    }
    if (mode === 'dispatch_resume' && (!taskId || !fs.existsSync(DISPATCH_SCRIPT))) {
      throw new Error('D06: managed task and dispatcher required; no fallback');
    }
    if (requestId != null && mode !== 'dispatch_resume') throw new Error('D13: request IDs are supported only for managed dispatch');
    if (retryOf != null && requestId == null) throw new Error('D13: retry requires new request ID');
    if (requestId != null && allowDuplicate) throw new Error('D13: allowDuplicate cannot bypass durable request identity');
    if (mode === 'readonly') {
      return this.startReadonlyAsk({
        threadId,
        prompt: cleanMsg,
        cwd,
        opType: 'readonly_ask',
      });
    }

    if (mode === 'dispatch_resume' && taskId && fs.existsSync(DISPATCH_SCRIPT)) {
      if (!this.pythonBin) throw new Error('Python executable not found; set PYTHON_BIN');
    } else if (!this.codexBin) throw new Error('Codex executable not found; set CODEX_BIN');
    const dedupKey = this.consoleDb.makeDedupKey(threadId, mode, cleanMsg);
    if (requestId == null && !allowDuplicate) {
      const dup = this.consoleDb.findRecentDuplicate(dedupKey, 60_000);
      if (dup) {
        throw new Error(
          `60秒内已投递过相同消息（操作 ${dup.id}，状态 ${dup.status}）。如需重发，请勾选「允许重复投递」。`
        );
      }
    }

    if (mode === 'dispatch_resume' && taskId && fs.existsSync(DISPATCH_SCRIPT)) {
      const rev=requestId==null?null:keyedEnvelope(cleanMsg,taskId,false);
      const actualCwd=safeCwd(cwd);
      const reservation=requestOp(this.consoleDb, requestId,
        ['resume',threadId,taskId,actualCwd,cleanMsg,rev,retryOf], {
        threadId,
        opType: 'dispatch_resume',
        prompt: cleanMsg,
        mode: 'dispatch_resume',
        dedupKey,
        meta: { taskId, cwd: actualCwd, revision:rev },
      });
      const op=reservation.op;
      if (!reservation.created) return {...op,duplicate:true};
      const dispatchArgs=[DISPATCH_SCRIPT, 'resume', '--task-id', taskId, '--no-network', '--prompt', cleanMsg];
      if (requestId!=null) dispatchArgs.push('--protocol-v2','--request-id',requestId);
      if (retryOf!=null) dispatchArgs.push('--retry-of',retryOf);
      const child = spawn(
        this.pythonBin,
        dispatchArgs,
        {
          cwd: safeCwd(cwd),
          env: buildExecEnv(),
          detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
        }
      );

      let stdout = '';
      let stderr = '';
      child.stdout.on('data', (c) => {
        if (stdout.length < 200_000) stdout += c.toString('utf8');
      });
      child.stderr.on('data', (c) => {
        if (stderr.length < 80_000) stderr += c.toString('utf8');
      });
      watchOwnedChild(child, 660_000, err => {
        this.consoleDb.finishOp(op.id,{status:'failed',errorText:err.message});
      }, (code,timedOut) => {
        let parsed = null;
        try { parsed = JSON.parse(stdout.trim()); } catch {}
        const outcome = requestId==null?classifyManagedResult(code,parsed,timedOut):classifyKeyedResult(code,parsed,taskId,rev,timedOut);
        this.consoleDb.finishOp(op.id, {
          status: outcome.status,
          outputText: stdout.trim(),
          errorText: outcome.error || stderr.trim() || null,
          metaPatch: {exitCode:code,taskStatus:outcome.taskStatus,processStatus:outcome.processStatus,verificationStatus:outcome.verificationStatus},
        });
      });
      return op;
    }

    throw new Error('D06: no authorized execution route');
  }

  /**
   * Spawn a new managed Codex worker via dispatch.py run
   */
  spawnWorker({
    cwd,
    prompt,
    taskId = '',
    difficulty = 'auto',
    quality = 'smart',
    isolation = 'worktree',
    network = false,
    changeKey = '',
    goalTitle = '',
    requestId = null,
    streamEvents = false,
  }) {
    if (typeof streamEvents !== 'boolean' || (streamEvents && requestId==null)) throw new Error('D14: streaming requires explicit v2 requestId');
    if (!this.pythonBin) throw new Error('Python executable not found; set PYTHON_BIN');
    if (!this.codexBin) throw new Error('Codex executable not found; set CODEX_BIN');
    if (network !== false) throw new Error('D06: network access denied; trusted host authorization unavailable');
    if (!['auto','low','medium','hard','extreme'].includes(difficulty) || !['smart','max','balanced'].includes(quality) || !['worktree','inplace','auto'].includes(isolation)) throw new Error('D06: invalid worker options');
    const cleanCwd = cwd ? safeCwd(cwd) : '';
    const cleanPrompt = (prompt || '').trim();
    if (!cleanCwd || !fs.existsSync(cleanCwd)) {
      throw new Error(`目标工作目录不存在: ${cleanCwd || '(空)'}`);
    }
    if (!cleanPrompt) {
      throw new Error('任务指令（Prompt）不能为空');
    }
    if (!fs.existsSync(DISPATCH_SCRIPT)) {
      throw new Error(`未找到多端调度脚本: ${DISPATCH_SCRIPT}`);
    }

    const useNetwork = false;
    // v2 short result intentionally omits session identity; avoid creating a
    // binding until the actual artifact/host identity has been verified.
    if (requestId!=null && (changeKey || goalTitle)) throw new Error('D13: keyed v2 binding not supported');
    const rev=requestId==null?null:keyedEnvelope(cleanPrompt,taskId,true);
    const reservation=requestOp(this.consoleDb,requestId,
      ['run',cleanCwd,taskId,cleanPrompt,rev,difficulty,quality,isolation,useNetwork,...(streamEvents?['stream-v1']:[])], {
      threadId:null,
      opType:'spawn_worker',
      prompt:cleanPrompt,
      mode:[quality,difficulty,isolation].join('/'),
      meta:{cwd:cleanCwd,taskId:taskId||null,changeKey:changeKey||null,network:useNetwork,revision:rev},
    });
    const op=reservation.op;
    if (!reservation.created) return {...op,duplicate:true};

    const args = [
      DISPATCH_SCRIPT,
      'run',
      '--cwd',
      cleanCwd,
      '--difficulty',
      difficulty,
      '--quality',
      quality,
      '--isolation',
      isolation,
      '--prompt',
      cleanPrompt,
    ];
    if (taskId && taskId.trim()) {
      args.push('--task-id', taskId.trim());
    }
    if (requestId!=null) args.push('--protocol-v2','--request-id',requestId);
    if (streamEvents) args.push('--stream-events');

    const child = spawn(this.pythonBin, args, {
      cwd: cleanCwd,
      env: buildExecEnv(),
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (c) => {
      if (stdout.length < 250_000) stdout += c.toString('utf8');
    });
    child.stderr.on('data', (c) => {
      if (stderr.length < 80_000) stderr += c.toString('utf8');
    });

    watchOwnedChild(child, 660_000, err => {
      this.consoleDb.finishOp(op.id,{status:'failed',errorText:'启动 dispatch.py 失败: '+err.message});
    }, (code,timedOut) => {
      let parsed = null;
      try {
        parsed = JSON.parse(stdout.trim());
      } catch {
        parsed = null;
      }
      const outcome = requestId==null?classifyManagedResult(code,parsed,timedOut):classifyKeyedResult(code,parsed,taskId,rev,timedOut);
      const sessionId = parsed?.session_id || null;
      const finalTaskId = parsed?.task_id || taskId || null;

      if (changeKey && changeKey.trim()) {
        try {
          this.consoleDb.upsertBinding({
            changeKey: changeKey.trim(),
            goalTitle: (goalTitle || '').trim() || cleanPrompt.slice(0, 80),
            threadId: sessionId,
            taskId: finalTaskId,
            ownerRole: 'codex',
            status: outcome.status === 'succeeded' ? 'reviewing' : 'blocked',
            repoPath: cleanCwd,
            branch: parsed?.branch || null,
            notes: parsed?.report?.summary || '',
          });
        } catch {
          // ignore binding failure
        }
      }

      this.consoleDb.finishOp(op.id, {
        status: outcome.status,
        outputText: parsed
          ? JSON.stringify(parsed, null, 2)
          : stdout.trim(),
        errorText: outcome.error || stderr.trim() || null,
        metaPatch: {
          exitCode: code,
          taskStatus: outcome.taskStatus,
          processStatus: outcome.processStatus,
          verificationStatus: outcome.verificationStatus,
          taskId: finalTaskId,
          sessionId,
          branch: parsed?.branch || null,
        },
      });
    });

    return op;
  }

  async inspectGit(cwd) {
    if (!cwd || !fs.existsSync(cwd)) {
      return { isGit: false, error: '工作目录不存在或已被清理', cwd };
    }
    const blackboardPath = path.join(cwd, 'docs', 'BLACKBOARD.md');
    const hasBlackboard = fs.existsSync(blackboardPath);
    try {
      if (!this.gitBin) throw new Error('Git executable not found; set GIT_BIN');
      const [{ stdout: branch }, { stdout: status }, { stdout: diffStat }] = await Promise.all([
        execFileAsync(this.gitBin, ['rev-parse', '--abbrev-ref', 'HEAD'], { cwd, timeout: 5000 }),
        execFileAsync(this.gitBin, ['status', '--porcelain=v1', '-z'], { cwd, timeout: 5000 }),
        execFileAsync(this.gitBin, ['diff', '--no-ext-diff', '--no-textconv', '--stat'], { cwd, timeout: 5000 }),
      ]);
      const files = parsePorcelainZ(status,cwd);
      return {
        isGit: true,
        cwd,
        branch: branch.trim(),
        statusShort: files.map(f=>`${f.xy} ${f.originalFile ? f.originalFile+' -> ' : ''}${f.file}`).join('\n'),
        diffStat: diffStat.trim(),
        files,
        hasBlackboard,
        blackboardPath: hasBlackboard ? blackboardPath : null,
      };
    } catch (err) {
      return {
        isGit: false,
        cwd,
        hasBlackboard,
        blackboardPath: hasBlackboard ? blackboardPath : null,
        error: (err.stderr || err.message || '非 Git 仓库').trim(),
      };
    }
  }
}
