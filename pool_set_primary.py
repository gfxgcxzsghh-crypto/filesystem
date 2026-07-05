#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把指定模型插到主号池最前面(当主力),原有号往后退当备用。改完重启主网关。
主网关按'顺序+健康'挑号、转发时用每条自己的 model(池子里各条 model 不同就证明如此),
所以把强模型放第一条 => claude 一敲就用它;它挂了自动落到后面的 opus 备用号。
全程备份 ai_pool.json -> .bak,可一键撤销。

用法: python3 pool_set_primary.py <模型> <key> [base]
例子: python3 pool_set_primary.py kr/claude-sonnet-4.5 sk-你的plus号key
需 root。"""
import os, sys, json, glob, subprocess, time, urllib.request, urllib.error

if len(sys.argv) < 3:
    print(__doc__)
    raise SystemExit(1)
MODEL = sys.argv[1]
KEY = sys.argv[2]
BASE = sys.argv[3] if len(sys.argv) > 3 else "https://omaleai.qzz.io/v1"
TOKEN = "sk-pool"

POOL = None
for p in ["/opt/ai_pool.json", "/root/ai_pool.json"] + glob.glob("/opt/**/ai_pool.json", recursive=True):
    if os.path.isfile(p):
        POOL = p
        break
if not POOL:
    print("[X] 没找到 ai_pool.json,发老板。")
    raise SystemExit(1)

d = json.load(open(POOL, encoding="utf-8"))
if not isinstance(d, list):
    print("[X] 池子不是数组,别乱改,发老板。")
    raise SystemExit(1)

# 备份
bak = POOL + ".bak"
json.dump(d, open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ 已备份:", bak)

# 去重(同 base+model 的老条目删掉)再插到最前
d = [it for it in d if not (isinstance(it, dict) and it.get("base") == BASE and it.get("model") == MODEL)]
d.insert(0, {"base": BASE, "key": KEY, "model": MODEL})
json.dump(d, open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ 已把 %s 放到号池第一条(主力),共 %d 个号。" % (MODEL, len(d)))
print("  顺序: " + " -> ".join("%s(%s)" % (i, (it.get('model') if isinstance(it, dict) else '?')) for i, it in enumerate(d)))

# 重启主网关
print("重启主网关 ...")
svc = None
out = subprocess.run(["bash", "-lc", "systemctl list-units --type=service 2>/dev/null | grep -iE 'gateway|ai_gateway'"],
                     stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore")
if out.strip():
    svc = out.split()[0]
if svc:
    subprocess.run(["systemctl", "restart", svc])
    print("✓ systemctl restart", svc)
else:
    subprocess.run(["bash", "-lc", "pkill -f ai_gateway.py"])
    time.sleep(1.5)
    subprocess.run(["bash", "-lc", "cd /opt && nohup python3 -u /opt/ai_gateway.py > /opt/ai_gateway.log 2>&1 &"])
    print("✓ 重新拉起主网关")
time.sleep(3)

# 验证: 网关活着 + 经 8787 真调一次,看实际用的是不是新模型
alive = subprocess.run(["bash", "-lc", "ps aux | grep ai_gateway.py | grep -v grep"],
                       stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print("主网关:", "活着 ✓" if alive else "没起来 ✗(看 /opt/ai_gateway.log)")

def probe(auth):
    body = json.dumps({"model": "claude-opus-4-8", "max_tokens": 64,
                       "messages": [{"role": "user", "content": "回一个字:好"}]}).encode()
    h = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    h.update(auth)
    req = urllib.request.Request("http://127.0.0.1:8787/v1/messages", data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

ok = False
for auth in ({"x-api-key": TOKEN}, {"Authorization": "Bearer " + TOKEN}):
    try:
        j = probe(auth)
        txt = "".join(b.get("text", "") for b in (j.get("content") or []) if isinstance(b, dict))
        if j.get("content"):
            print("✓ 经主网关测通,实际模型=%s 回复=%s" % (j.get("model", "?"), (txt or "有回复")[:40]))
            ok = True
            break
    except urllib.error.HTTPError as e:
        print("  (%s: %s)" % (list(auth)[0], e.code))
    except Exception as e:
        print("  (", str(e)[:80], ")")
if not ok:
    print("[!] 测试没过。想立刻撤回旧池子: cp %s %s 再重启网关。" % (bak, POOL))

print("\n=========== 完成 ===========")
print("现在 claude 一敲就先用: %s(免费真 Claude),它挂了自动落到你的 opus 备用号。" % MODEL)
print("想换回 opus 优先/撤销: cp %s %s && pkill -f ai_gateway.py && (cd /opt && nohup python3 -u /opt/ai_gateway.py >/opt/ai_gateway.log 2>&1 &)" % (bak, POOL))
