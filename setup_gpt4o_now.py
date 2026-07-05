#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开一个只跑 gpt-4o 的专用网关(端口 8788),给个 `claude4o` 命令立刻能用。
不动主网关(8787)、不动主池子、不动主号。复用池子里已有的 o站 key(不需手输)。
做法: 把你现成能用的 ai_gateway.py 复制一份,只把'池子文件'和'端口'换掉,
      另起一个实例。这样翻译逻辑跟主网关完全一样,最稳。
用法: python3 setup_gpt4o_now.py   (需 root)"""
import os, re, json, glob, subprocess, time, urllib.request, urllib.error

GW = "/opt/ai_gateway.py"
if not os.path.isfile(GW):
    hit = glob.glob("/opt/**/ai_gateway.py", recursive=True) + glob.glob("/root/**/ai_gateway.py", recursive=True)
    GW = hit[0] if hit else None
POOL = None
for p in ["/opt/ai_pool.json", "/root/ai_pool.json"] + glob.glob("/opt/**/ai_pool.json", recursive=True):
    if os.path.isfile(p):
        POOL = p
        break
if not GW or not POOL:
    print("[X] 没找到 ai_gateway.py 或 ai_pool.json,发老板。")
    raise SystemExit(1)
print("主网关:", GW, "| 主池子:", POOL)

# 1) 复用池子里的 o站 key
d = json.load(open(POOL, encoding="utf-8"))
o_key = None
for it in (d if isinstance(d, list) else []):
    if isinstance(it, dict) and "omaleai" in str(it.get("base", "")):
        o_key = it.get("key")
        break
if not o_key:
    print("[X] 池子里没有 o站(omaleai)号,拿不到 key。发老板。")
    raise SystemExit(1)
print("✓ 复用 o站 key: %s…%s" % (o_key[:6], o_key[-4:]))
BASE = "https://omaleai.qzz.io/v1"
TOKEN = "sk-pool"  # 跟主网关一样的对内令牌(Claude Code settings 里就是它)

# 2) 只跑 gpt-4o 的小池子
GPOOL = "/opt/ai_pool_gpt4o.json"
json.dump([{"base": BASE, "key": o_key, "model": "gpt-4o"}],
          open(GPOOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ 写好 gpt-4o 专用池子:", GPOOL)

# 3) 复制网关,只换'池子文件名'和'端口 8787->8788'
src = open(GW, encoding="utf-8", errors="ignore").read()
new = src.replace("ai_pool.json", "ai_pool_gpt4o.json")
n_port = new.count("8787")
new = new.replace("8787", "8788")
GGW = "/opt/ai_gateway_gpt4o.py"
open(GGW, "w", encoding="utf-8").write(new)
print("✓ 生成专用网关:", GGW, "(改了 %d 处端口)" % n_port)
if "ai_pool_gpt4o.json" not in new:
    print("[!] 没在网关里找到 'ai_pool.json' 字样——它可能从参数/环境读池子。仍尝试启动,不行发老板。")
if n_port == 0:
    print("[!] 没在网关里找到端口 8787——可能端口写在别处。仍尝试启动,若 8788 没起来发老板。")

# 4) 起专用网关
subprocess.run(["bash", "-lc", "pkill -f ai_gateway_gpt4o.py"])
time.sleep(1)
subprocess.run(["bash", "-lc",
                "cd /opt && nohup python3 -u /opt/ai_gateway_gpt4o.py > /opt/ai_gateway_gpt4o.log 2>&1 &"])
time.sleep(3)
port = subprocess.run(["bash", "-lc", "ss -ltnp 2>/dev/null | grep 8788 || netstat -ltnp 2>/dev/null | grep 8788"],
                      stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print("8788 端口:", "在听 ✓" if port else "没听到 ✗(看 /opt/ai_gateway_gpt4o.log 末尾)")
if not port:
    tail = subprocess.run(["bash", "-lc", "tail -n 15 /opt/ai_gateway_gpt4o.log 2>/dev/null"],
                          stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore")
    print("--- 日志末尾 ---\n" + tail)

# 5) 经 8788 用 Anthropic 格式(claude 就是这么发的)真测一次 gpt-4o
def try_msg(auth_hdr):
    body = json.dumps({"model": "gpt-4o", "max_tokens": 64,
                       "messages": [{"role": "user", "content": "回一个字:好"}]}).encode()
    h = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    h.update(auth_hdr)
    req = urllib.request.Request("http://127.0.0.1:8788/v1/messages", data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

ok = False
if port:
    for auth in ({"x-api-key": TOKEN}, {"Authorization": "Bearer " + TOKEN}):
        try:
            j = try_msg(auth)
            txt = ""
            for blk in (j.get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "text":
                    txt += blk.get("text", "")
            if txt.strip() or j.get("content"):
                print("✓ 经 8788 测 gpt-4o 成功,回复:", (txt or json.dumps(j, ensure_ascii=False))[:60])
                ok = True
                break
        except urllib.error.HTTPError as e:
            print("  (%s 认证试了下: %s)" % (list(auth)[0], e.code))
        except Exception as e:
            print("  (试了下:", str(e)[:80], ")")
if port and not ok:
    print("[!] 8788 起来了但测试没过,可能认证头不一样。命令仍给你,先试;不行发老板看日志。")

# 6) 专用配置目录 + claude4o 命令
CFG = "/opt/claude4o-cfg"
os.makedirs(CFG, exist_ok=True)
json.dump({"env": {"ANTHROPIC_BASE_URL": "http://127.0.0.1:8788",
                   "ANTHROPIC_AUTH_TOKEN": TOKEN, "ANTHROPIC_MODEL": "gpt-4o"}},
          open(os.path.join(CFG, "settings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
launcher = ("#!/bin/bash\n"
            "# 用 gpt-4o 跑 Claude Code(专用通道 8788),不影响普通的 claude(主号)\n"
            "export CLAUDE_CONFIG_DIR=%s\n"
            "export ANTHROPIC_BASE_URL=http://127.0.0.1:8788\n"
            "export ANTHROPIC_AUTH_TOKEN=%s\n"
            "export ANTHROPIC_MODEL=gpt-4o\n"
            'exec claude "$@"\n') % (CFG, TOKEN)
LP = "/usr/local/bin/claude4o"
open(LP, "w").write(launcher)
os.chmod(LP, 0o755)
print("✓ 写好命令:", LP)

print("\n=========== 完成 ===========")
print("现在想用 gpt-4o 版 Claude Code,直接敲:  claude4o")
print("想用回主号(opus),照常敲:            claude")
print("专用网关日志: /opt/ai_gateway_gpt4o.log")
print("想关掉 gpt-4o 通道: pkill -f ai_gateway_gpt4o.py")
