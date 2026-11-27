import { execFile, spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const DISPATCH_SCRIPT = path.join(
  os.homedir(),
  '.gemini',
  'config',
  'skills',
  'multi-agent-dispatch',
  'scripts',
  'dispatch.py'
);

export const DIAGNOSE_BLOCKER_PROMPT =
  '请基于当前完整上下文和 Goal 目标，用 3~5 条要点精炼说明：' +
  '1) 当前明确卡点或阻塞原因是什么；' +
  '2) 已完成和未完成的关键项分别是什么；' +
  '3) 需要用户或主控做出的下一步最小决策/动作是什么。' +
  '请严格保持只读，不要修改任何文件或执行写操作。';

function isExecutable(p) {
  if (!p) return false;
  try {
    fs.accessSync(p, fs.constants.X_OK);
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
}

export function resolveCodexBin() {
  const candidates = [
    process.env.CODEX_BIN,
    '/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex',
    path.join(os.homedir(), '.local', 'bin', 'codex'),
    path.join(os.homedir(), '.npm-global', 'bin', 'codex'),
    path.join(os.homedir(), '.volta', 'bin', 'codex'),
    '/opt/homebrew/bin/codex',
    '/usr/local/bin/codex',
  ];
  for (const c of candidates) {
    if (isExecutable(c)) return c;
  }
  return 'codex';
}

export function resolvePythonBin() {
  const candidates = [
    process.env.PYTHON_BIN,
    path.join(os.homedir(), '.local', 'bin', 'python3'),
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
    '/usr/bin/python3',
  ];
  for (const c of candidates) {
    if (isExecutable(c)) return c;
  }
  return 'python3';
}

export function buildExecEnv() {
  const extraPaths = [
    path.join(os.homedir(), '.local', 'bin'),
    path.join(os.homedir(), '.npm-global', 'bin'),
    path.join(os.homedir(), '.volta', 'bin'),
    '/opt/homebrew/bin',
    '/usr/local/bin',
  ];
  const curPath = process.env.PATH || '';
  return {
    ...process.env,
    PATH: [...extraPaths, curPath].filter(Boolean).join(path.delimiter),
  };
}

function safeCwd(cwd) {
  if (cwd && fs.existsSync(cwd)) {
    try {
      if (fs.statSync(cwd).isDirectory()) return cwd;
    } catch {
      // fallback
    }
  }
  return os.homedir();
}

export class CodexRunner {
  constructor(consoleDb) {
    this.consoleDb = consoleDb;
    this.codexBin = resolveCodexBin();
    this.pythonBin = resolvePythonBin();
  }

  getRuntimeInfo() {
    return {
      codexBin: this.codexBin,
      dispatchAvailable: fs.existsSync(DISPATCH_SCRIPT),
      dispatchScript: DISPATCH_SCRIPT,
    };
  }

  /**
   * Non-destructive read-only question / blocker diagnosis via `codex exec fork --ephemeral`
   */
  startReadonlyAsk({ threadId, prompt, cwd, opType = 'readonly_ask' }) {
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
      'approval_policy="never"',
      '-o',
      outFile,
      threadId,
      actualPrompt,
    ];

    const child = spawn(this.codexBin, args, {
      cwd: safeCwd(cwd),
      env: buildExecEnv(),
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

    const timer = setTimeout(() => {
      try {
        child.kill('SIGTERM');
      } catch {
        // ignore
      }
    }, 180_000);

    child.on('error', (err) => {
      clearTimeout(timer);
      this.consoleDb.finishOp(op.id, {
        status: 'failed',
        errorText: `启动 codex 失败: ${err.message}`,
      });
    });

    child.on('close', (code) => {
      clearTimeout(timer);
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
      if (code === 0 && outputText) {
        this.consoleDb.finishOp(op.id, {
          status: 'succeeded',
          outputText,
          errorText: stderr.trim() || null,
          metaPatch: { exitCode: code },
        });
      } else {
        this.consoleDb.finishOp(op.id, {
          status: code === 0 ? 'succeeded' : 'failed',
          outputText: outputText || '',
          errorText:
            stderr.trim() ||
            (code !== 0 ? `codex exec fork 退出码 ${code}` : '未返回正文内容'),
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
  }) {
    const cleanMsg = (message || '').trim();
    if (!cleanMsg) {
      throw new Error('消息内容不能为空');
    }

    if (mode === 'readonly') {
      return this.startReadonlyAsk({
        threadId,
        prompt: cleanMsg,
        cwd,
        opType: 'readonly_ask',
      });
    }

    const dedupKey = this.consoleDb.makeDedupKey(threadId, mode, cleanMsg);
    if (!allowDuplicate) {
      const dup = this.consoleDb.findRecentDuplicate(dedupKey, 60_000);
      if (dup) {
        throw new Error(
          `60秒内已投递过相同消息（操作 ${dup.id}，状态 ${dup.status}）。如需重发，请勾选「允许重复投递」。`
        );
      }
    }

    if (mode === 'queue') {
      const op = this.consoleDb.createOp({
        threadId,
        opType: 'queue_send',
        prompt: cleanMsg,
        mode: 'queue',
        dedupKey,
        meta: { cwd: safeCwd(cwd) },
      });

      const args = ['queue', '--thread', threadId, '--message', cleanMsg, '--resume'];
      const validCwd = safeCwd(cwd);
      if (cwd && validCwd === cwd) {
        args.push('-C', validCwd);
      }

      try {
        const { stdout, stderr } = await execFileAsync(this.codexBin, args, {
          cwd: validCwd,
          env: buildExecEnv(),
          timeout: 30_000,
          maxBuffer: 1024 * 1024,
        });
        return this.consoleDb.finishOp(op.id, {
          status: 'succeeded',
          outputText: (stdout || '').trim() || '消息已入队并触发唤醒（codex queue --resume）',
          errorText: (stderr || '').trim() || null,
          metaPatch: { exitCode: 0 },
        });
      } catch (err) {
        return this.consoleDb.finishOp(op.id, {
          status: 'failed',
          outputText: (err.stdout || '').trim(),
          errorText: (err.stderr || err.message || 'codex queue 执行失败').trim(),
          metaPatch: { exitCode: err.code ?? -1 },
        });
      }
    }

    if (mode === 'dispatch_resume' && taskId && fs.existsSync(DISPATCH_SCRIPT)) {
      const op = this.consoleDb.createOp({
        threadId,
        opType: 'dispatch_resume',
        prompt: cleanMsg,
        mode: 'dispatch_resume',
        dedupKey,
        meta: { taskId, cwd: safeCwd(cwd) },
      });

      const child = spawn(
        this.pythonBin,
        [DISPATCH_SCRIPT, 'resume', '--task-id', taskId, '--prompt', cleanMsg],
        {
          cwd: safeCwd(cwd),
          env: buildExecEnv(),
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
      child.on('close', (code) => {
        this.consoleDb.finishOp(op.id, {
          status: code === 0 ? 'succeeded' : 'failed',
          outputText: stdout.trim(),
          errorText: stderr.trim() || (code !== 0 ? `dispatch resume 退出码 ${code}` : null),
          metaPatch: { exitCode: code },
        });
      });
      return op;
    }

    // Default async exec resume
    const op = this.consoleDb.createOp({
      threadId,
      opType: 'exec_resume',
      prompt: cleanMsg,
      mode: 'resume',
      dedupKey,
      meta: { cwd: safeCwd(cwd) },
    });

    const outFile = path.join(os.tmpdir(), `codex-console-resume-${op.id}.txt`);
    const child = spawn(
      this.codexBin,
      ['exec', 'resume', '--skip-git-repo-check', '-o', outFile, threadId, cleanMsg],
      {
        cwd: safeCwd(cwd),
        env: buildExecEnv(),
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
    child.on('error', (err) => {
      this.consoleDb.finishOp(op.id, {
        status: 'failed',
        errorText: `启动 codex exec resume 失败: ${err.message}`,
      });
    });
    child.on('close', (code) => {
      let finalMsg = '';
      if (fs.existsSync(outFile)) {
        try {
          finalMsg = fs.readFileSync(outFile, 'utf8').trim();
          fs.unlinkSync(outFile);
        } catch {
          // ignore
        }
      }
      this.consoleDb.finishOp(op.id, {
        status: code === 0 ? 'succeeded' : 'failed',
        outputText: finalMsg || stdout.trim(),
        errorText: stderr.trim() || (code !== 0 ? `codex exec resume 退出码 ${code}` : null),
        metaPatch: { exitCode: code },
      });
    });

    return op;
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
  }) {
    const cleanCwd = (cwd || '').trim();
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

    const useNetwork = Boolean(network);
    const op = this.consoleDb.createOp({
      threadId: null,
      opType: 'spawn_worker',
      prompt: cleanPrompt,
      mode: `${quality}/${difficulty}/${isolation}${useNetwork ? '/net' : ''}`,
      meta: { cwd: cleanCwd, taskId: taskId || null, changeKey: changeKey || null, network: useNetwork },
    });

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
    if (useNetwork) {
      args.push('--network');
    }
    if (taskId && taskId.trim()) {
      args.push('--task-id', taskId.trim());
    }

    const child = spawn(this.pythonBin, args, {
      cwd: cleanCwd,
      env: buildExecEnv(),
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

    child.on('error', (err) => {
      this.consoleDb.finishOp(op.id, {
        status: 'failed',
        errorText: `启动 dispatch.py 失败: ${err.message}`,
      });
    });

    child.on('close', (code) => {
      let parsed = null;
      try {
        parsed = JSON.parse(stdout.trim());
      } catch {
        parsed = null;
      }
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
            status: code === 0 ? 'completed' : 'blocked',
            repoPath: cleanCwd,
            branch: parsed?.branch || null,
            notes: parsed?.summary || '',
          });
        } catch {
          // ignore binding failure
        }
      }

      this.consoleDb.finishOp(op.id, {
        status: code === 0 ? 'succeeded' : 'failed',
        outputText: parsed
          ? JSON.stringify(parsed, null, 2)
          : stdout.trim(),
        errorText: stderr.trim() || (code !== 0 ? `dispatch.py 退出码 ${code}` : null),
        metaPatch: {
          exitCode: code,
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
      const [{ stdout: branch }, { stdout: status }, { stdout: diffStat }] = await Promise.all([
        execFileAsync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], { cwd, timeout: 5000 }),
        execFileAsync('git', ['status', '--short'], { cwd, timeout: 5000 }),
        execFileAsync('git', ['diff', '--stat'], { cwd, timeout: 5000 }),
      ]);
      const files = status
        .split('\n')
        .map((l) => l.trimEnd())
        .filter(Boolean)
        .map((line) => ({
          xy: line.slice(0, 2).trim() || 'M',
          file: line.slice(3).trim(),
          absPath: path.join(cwd, line.slice(3).trim()),
        }));
      return {
        isGit: true,
        cwd,
        branch: branch.trim(),
        statusShort: status.trim(),
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
