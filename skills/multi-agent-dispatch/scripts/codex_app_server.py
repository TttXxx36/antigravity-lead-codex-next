"""D20 experimental stdio probe adapter. No production turn dispatch or auto replay.

Only an explicitly supplied owned process is used. The production dispatcher does
not construct one. JSON-RPC mutation methods are structurally unavailable.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

MAX_LINE=65536
MAX_FRAMES=256
MAX_STDERR=1048576
MAX_REQUESTS=64
VERSION=re.compile(r"(?:codex-cli\s+|codex_cli_rs/|codex/)(\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)\b")
IDENTITY=re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
USAGE_FIELDS=("inputTokens","cachedInputTokens","outputTokens","reasoningOutputTokens","totalTokens")

class ProtocolError(RuntimeError):pass


def strict_frame(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_LINE or not raw.endswith(b"\n"):
        raise ProtocolError("D20: truncated or oversized frame")
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError("duplicate key")
            result[k]=v
        return result
    def constant(_):raise ValueError("nonfinite number")
    try:obj=json.loads(raw.decode("utf8"),object_pairs_hook=unique,parse_constant=constant)
    except (ValueError,UnicodeError,RecursionError) as exc:raise ProtocolError("D20: invalid JSONL") from exc
    if not isinstance(obj,dict):raise ProtocolError("D20: object frame required")
    return obj


def version_of(value):
    if not isinstance(value,str) or len(value)>1024:return None
    match=VERSION.search(value)
    return match[1] if match else None


def same_path(a,b):
    try:
        return (isinstance(a,str) and Path(a).is_absolute() and
                os.path.normcase(str(Path(a).resolve(strict=True)))==os.path.normcase(str(Path(b).resolve(strict=True))))
    except (OSError,ValueError,RuntimeError):return False


def policy_matches(response,cwd,sandbox,model=None,effort=None):
    """Compare only known effective metadata, never infer actual enforcement."""
    if not isinstance(response,dict) or response.get("approvalPolicy")!="never" or not same_path(response.get("cwd"),cwd):return False
    if any(response.get(k) is not None for k in ("activePermissionProfile","permissionProfile","permissions")):return False
    if model is not None and response.get("model")!=model:return False
    if effort is not None and response.get("reasoningEffort")!=effort:return False
    p=response.get("sandbox")
    if not isinstance(p,dict) or p.get("networkAccess") is not False:return False
    if sandbox=="read-only":return set(p)=={"type","networkAccess"} and p["type"]=="readOnly"
    if sandbox!="workspace-write" or set(p)!={"type","networkAccess","writableRoots","excludeTmpdirEnvVar","excludeSlashTmp"}:return False
    roots=p["writableRoots"]
    return (p["type"]=="workspaceWrite" and p["excludeTmpdirEnvVar"] is True and p["excludeSlashTmp"] is True and
            isinstance(roots,list) and 1<=len(roots)<=16 and all(same_path(root,cwd) for root in roots))


class UsageSnapshot:
    """Thread cumulative totals; do not add 'last' or generic usage payloads."""
    def __init__(self,thread_id,turn_id):
        if not all(isinstance(x,str) and IDENTITY.fullmatch(x) for x in (thread_id,turn_id)):raise ValueError("D20: invalid identity")
        self.thread_id=thread_id;self.turn_id=turn_id;self.total=None;self.integrity="unknown";self.gap=False
    def disconnect(self):self.gap=True;self.integrity="unknown"
    def observe(self,event):
        if event.get("method")!="thread/tokenUsage/updated":return
        p=event.get("params")
        if not isinstance(p,dict) or p.get("threadId")!=self.thread_id or p.get("turnId")!=self.turn_id:return
        u=p.get("tokenUsage");t=u.get("total") if isinstance(u,dict) else None
        if not isinstance(t,dict) or any(type(t.get(k)) is not int or not 0<=t[k]<=2**53-1 for k in USAGE_FIELDS):
            self.disconnect();return
        v={k:t[k] for k in USAGE_FIELDS}
        if "cacheWriteInputTokens" in t:
            if type(t["cacheWriteInputTokens"]) is not int or not 0<=t["cacheWriteInputTokens"]<=2**53-1:self.disconnect();return
            v["cacheWriteInputTokens"]=t["cacheWriteInputTokens"]
        if v["cachedInputTokens"]>v["inputTokens"] or v["reasoningOutputTokens"]>v["outputTokens"]:
            self.disconnect();return
        if self.total is not None and (set(v)!=set(self.total) or any(v[k]<self.total[k] for k in v)):
            self.disconnect();return
        self.total=v;self.integrity="observed" if not self.gap else "unknown"
    def receipt(self):
        return {"source":"thread/tokenUsage/updated.tokenUsage.total","scope":"thread_cumulative_not_spend",
                "threadId":self.thread_id,"turnId":self.turn_id,"total":self.total.copy() if self.total is not None else None,
                "integrity":self.integrity,"gap":self.gap,"billableUsage":None}


def terminal_claim(event,thread_id,turn_id):
    if not isinstance(event,dict) or event.get("method")!="turn/completed":return None
    p=event.get("params");t=p.get("turn") if isinstance(p,dict) else None
    if not isinstance(t,dict) or p.get("threadId")!=thread_id or t.get("id")!=turn_id:return None
    status=t.get("status")
    if status not in ("completed","failed","interrupted"):return None
    return {"threadId":thread_id,"turnId":turn_id,"workerStatus":status,"accepted":False,"mergeAuthorized":False}


class ProbeConnection:
    """Single synchronous owner, bounded binary stdio; no generic RPC entrypoint."""
    def __init__(self,argv,cwd,env,expected_version,timeout=3,usage=None):
        if not isinstance(expected_version,str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?",expected_version):raise ValueError("D20: exact probed version required")
        if not 0<timeout<=10:raise ValueError("D20: invalid timeout")
        self.version=expected_version;self.timeout=timeout;self.usage=usage;self.proc=None
        self.queue=queue.Queue(32);self.fault=threading.Event();self.closed=False;self.seq=0;self.ready=False
        self.stderr_bytes=0;self.frames=0;self.threads=[];self.terminal=None
        try:
            self.proc=subprocess.Popen(list(argv),cwd=str(cwd),env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.threads=[threading.Thread(target=self._reader,daemon=True),threading.Thread(target=self._stderr,daemon=True)]
            for t in self.threads:t.start()
            result=self._call("initialize",{"clientInfo":{"name":"antigravity_lead","title":"Antigravity Lead probe","version":"1.0.0"},"capabilities":{"experimentalApi":False}})
            if (version_of(result.get("userAgent"))!=expected_version or not isinstance(result.get("platformFamily"),str)
                or not isinstance(result.get("platformOs"),str) or not isinstance(result.get("codexHome"),str)):
                raise ProtocolError("D20: incompatible initialize receipt")
            self._send({"method":"initialized"});self.ready=True
        except BaseException:
            self.close();raise
    def _reader(self):
        try:
            while True:
                raw=self.proc.stdout.readline(MAX_LINE+1)
                if not raw:break
                self.frames+=1
                if self.frames>MAX_FRAMES:raise ProtocolError("D20: frame limit")
                msg=strict_frame(raw)
                self.queue.put_nowait(msg)
        except (OSError,ProtocolError,queue.Full):self.fault.set()
        finally:
            try:self.proc.stdout.close()
            except OSError:pass
            self.fault.set()
    def _stderr(self):
        try:
            while True:
                raw=self.proc.stderr.read1(8192)
                if not raw:break
                self.stderr_bytes+=len(raw)
                if self.stderr_bytes>MAX_STDERR:self.fault.set();break
        except OSError:self.fault.set()
        finally:
            try:self.proc.stderr.close()
            except OSError:pass
    def _send(self,msg):
        # No turn/start, thread/start, resume, exec, account, or approval replies.
        if msg.get("method") not in ("initialize","initialized","thread/read"):
            raise ProtocolError("D20: mutation RPC unavailable")
        if self.closed or self.fault.is_set():raise ProtocolError("D20: disconnected")
        payload=json.dumps(msg,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode("ascii")+b"\n"
        if len(payload)>4096:raise ProtocolError("D20: oversized request")
        completed=threading.Event();error=[]
        def write():
            try:self.proc.stdin.write(payload);self.proc.stdin.flush()
            except (OSError,ValueError):error.append(True)
            finally:completed.set()
        threading.Thread(target=write,daemon=True).start()
        if not completed.wait(self.timeout) or error:raise ProtocolError("D20: write failed")
    def _call(self,method,params):
        if method not in ("initialize","thread/read") or self.seq>=MAX_REQUESTS:raise ProtocolError("D20: request unavailable or limit")
        if (method=="initialize" and self.seq!=0) or (method=="thread/read" and not self.ready):raise ProtocolError("D20: handshake required")
        self.seq+=1;ident=self.seq;self._send({"id":ident,"method":method,"params":params})
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            if self.fault.is_set():raise ProtocolError("D20: broken stream")
            try:msg=self.queue.get(timeout=min(.05,max(0,deadline-time.monotonic())))
            except queue.Empty:continue
            if "method" in msg:
                if "id" in msg:raise ProtocolError("D20: server request/approval denied")
                if self.usage is not None:
                    self.usage.observe(msg)
                    claim=terminal_claim(msg,self.usage.thread_id,self.usage.turn_id)
                    if claim is not None:
                        if self.terminal is not None and self.terminal!=claim:raise ProtocolError("D20: conflicting terminal state")
                        self.terminal=claim
                continue
            if type(msg.get("id")) is not int or msg["id"]!=ident or "error" in msg or not isinstance(msg.get("result"),dict):
                raise ProtocolError("D20: unmatched, unsupported or invalid response")
            return msg["result"]
        raise ProtocolError("D20: request deadline")
    def read_thread(self,thread_id):
        if not isinstance(thread_id,str) or not IDENTITY.fullmatch(thread_id):raise ValueError("D20: invalid thread identity")
        try:
            result=self._call("thread/read",{"threadId":thread_id,"includeTurns":False})
            t=result.get("thread");status=t.get("status") if isinstance(t,dict) else None
            if not isinstance(t,dict) or t.get("id")!=thread_id or not isinstance(status,dict) or status.get("type") not in ("notLoaded","idle","systemError","active"):
                raise ProtocolError("D20: invalid session receipt")
            return {"threadId":thread_id,"status":status["type"],"serverVersion":self.version,"readOnly":True,"accepted":False}
        except BaseException:
            if self.usage is not None:self.usage.disconnect()
            self.close();raise
    def close(self):
        if self.closed:return
        self.closed=True;self.ready=False
        if self.proc is not None:
            if self.proc.poll() is None:
                try:self.proc.terminate();self.proc.wait(timeout=1)
                except (OSError,subprocess.TimeoutExpired):
                    if self.proc.poll() is None:self.proc.kill()
                    try:self.proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:pass
            try:self.proc.stdin.close()
            except (OSError,ValueError):pass
            for t in self.threads:t.join(timeout=.3)
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


class ProbeSession:
    def __init__(self,argv,cwd,env,version,timeout=3,usage=None):
        self.args=(tuple(argv),cwd,env,version,timeout,usage);self.connection=None;self.spawns=0;self.usage=usage
    def connect(self):
        if self.connection is not None:raise ProtocolError("D20: explicit reconnect required")
        self.connection=ProbeConnection(*self.args);self.spawns+=1
        return self.connection
    def read(self,thread_id):
        if self.connection is None:raise ProtocolError("D20: connect first")
        return self.connection.read_thread(thread_id)
    def reconnect(self):
        if self.connection is not None:self.connection.close();self.connection=None
        if self.usage is not None:self.usage.disconnect()
        return self.connect()
    def close(self):
        if self.connection is not None:self.connection.close();self.connection=None
    def __enter__(self):self.connect();return self
    def __exit__(self,*_):self.close()
