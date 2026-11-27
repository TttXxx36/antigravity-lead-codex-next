"""Offline app-server protocol fixture; never launches a model or another process."""
import json
import sys
from pathlib import Path
import time
mode,log=sys.argv[1:3]
def send(value):
    print(json.dumps(value,separators=(",",":")),flush=True)
def record(method):
    with Path(log).open("a",encoding="utf8") as f:f.write(method+"\n")
ready=False
for line in sys.stdin:
    msg=json.loads(line);m=msg.get("method");record(m or "invalid")
    if m=="initialize":
        if mode=="version_mismatch":version="0.0.1"
        else:version="0.170.0"
        send({"id":msg["id"],"result":{"userAgent":"codex_cli_rs/"+version,"platformFamily":"fixture","platformOs":"fixture","codexHome":"fixture"}})
    elif m=="initialized":
        ready=True
    elif m=="thread/read" and ready and msg["params"].get("includeTurns") is False:
        tid=msg["params"]["threadId"];ident=msg["id"]
        if mode=="disconnect":sys.exit(0)
        if mode=="timeout":time.sleep(20)
        if mode=="approval":send({"id":99,"method":"item/commandExecution/requestApproval","params":{}})
        if mode=="malformed":print('{"id":2,"id":3,"result":{}}',flush=True);continue
        if mode=="oversize":print("x"*70000,flush=True);continue
        if mode=="wrong_id":ident+=1
        if mode=="unsupported":send({"id":ident,"error":{"code":-32601,"message":"unsupported"}});continue
        if mode=="wrong_thread":tid="wrong"
        total={"inputTokens":10,"cachedInputTokens":2,"outputTokens":5,"reasoningOutputTokens":1,"totalTokens":15}
        if mode in ("normal","wrong_thread"):
            for _ in range(2):
                send({"method":"thread/tokenUsage/updated","params":{"threadId":tid,"turnId":"turn-fixture","tokenUsage":{"last":total,"total":total}}})
            send({"method":"turn/completed","params":{"threadId":tid,"turn":{"id":"turn-fixture","status":"completed","items":[]}}})
        send({"id":ident,"result":{"thread":{"id":tid,"status":{"type":"idle"},"turns":[],"preview":"never expose raw preview"}}})
    else:sys.exit(9)
