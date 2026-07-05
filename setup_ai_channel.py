#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 Claude Code 开一个"指定模型"的专用通道(独立小网关+独立命令),立刻能用。
不动主网关(8787)、不动主池子、不动主号。复用你现成能用的 ai_gateway.py 翻译逻辑。

用法:
  python3 setup_ai_channel.py <模型> <端口> <命令名> [key] [base]
例子:
  # 装真 Claude Sonnet 4.5(用 plus号 key):
  python3 setup_ai_channel.py kr/claude-sonnet-4.5 8789 claudes45 sk-你的plus号key
  # 装 gpt-4o(复用池子里的 o站免费号,key 可省):
  python3 setup_ai_channel.py gpt-4o 8788 claude4o
说明: key 省略时,自动复用主池子里已有的 o站(omaleai) key;base 省略默认 o站。
"""
import os, sys, json, glob, subprocess, time, urllib.request, urllib.error

if len(sys.argv) < 4:
    print(__doc__)
    raise SystemExit(1)
MODEL = sys.argv[1]
PORT = sys.argv[2]
NAME = sys.argv[3]
KEY = sys.argv[4] if len(sys.argv) > 4 else None
BASE = sys.argv[5] if len(sys.argv) > 5 else "https://omaleai.qzz.io/v1"
TOKEN = "sk-pool"  # 跟主网关一致的对内令牌

GW = "/opt/ai_gateway.py"
if not os.path.isfile(GW):
    hit = glob.glob("/opt/**/ai_gateway.py", recursive=True)
    GW = hit[0] if hit else None
POOL = None
for p in ["/opt/ai_pool.json", "/root/ai_pool.json"] + glob.glob("/opt/**/ai_pool.json", recursive=True):
    if os.path.isfile(p):
        POOL = p
        break
if not GW:
    print("[X] 没找到 ai_gateway.py,发老板。")
    raise SystemExit(1)

# key: 没给就从主池子复用 o站 的
if not KEY:
    if not POOL:
        print("[X] 没给 key 又找不到主池子,发老板。")
        raise SystemExit(1)
    d = json.load(open(POOL, encoding="utf-8"))
    for it in (d if isinstance(d, list) else []):
        if isinstance(it, dict) and "omaleai" in str(it.get("base", "")):
            KEY = it.get("key")
            break
    if not KEY:
        print("[X] 池子里没有 o站号,请在命令末尾把 key 带上。")
        raise SystemExit(1)
    print("✓ 复用池子里的 o站 key: %s…%s" % (KEY[:6], KEY[-4:]))
else:
    print("✓ 用命令里给的 key: %s…%s" % (KEY[:6], KEY[-4:]))

# 1) 专用小池子(只一个模型)
gpool = "/opt/ai_pool_%s.json" % NAME
json.dump([{"base": BASE, "key": KEY, "model": MODEL}],
          open(gpool, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("✓ 写好专用池子:", gpool, "->", MODEL)

# 2) 复制网关: 换池子文件名 + 端口
src = open(GW, encoding="utf-8", errors="ignore").read()
new = src.replace("ai_pool.json", os.path.basename(gpool))
nport = new.count("8787")
new = new.replace("8787", str(PORT))
ggw = "/opt/ai_gateway_%s.py" % NAME
open(ggw, "w", encoding="utf-8").write(new)
print("✓ 生成专用网关:", ggw, "(端口改了 %d 处 -> %s)" % (nport, PORT))
if os.path.basename(gpool) not in new:
    print("[!] 网关里没找到 'ai_pool.json' 字样,可能从参数/环境读池子。仍尝试启动。")
if nport == 0:
    print("[!] 网关里没找到 8787,端口可能写别处。若 %s 没起来发老板。" % PORT)

# 3) 起专用网关
subprocess.run(["bash", "-lc", "pkill -f ai_gateway_%s.py" % NAME])
time.sleep(1)
subprocess.run(["bash", "-lc",
                "cd /opt && nohup python3 -u %s > /opt/ai_gateway_%s.log 2>&1 &" % (ggw, NAME)])
time.sleep(3)
listening = subprocess.run(["bash", "-lc",
                            "ss -ltnp 2>/dev/null | grep %s || netstat -ltnp 2>/dev/null | grep %s" % (PORT, PORT)],
                           stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print("端口 %s:" % PORT, "在听 ✓" if listening else "没听到 ✗(看 /opt/ai_gateway_%s.log)" % NAME)
if not listening:
    tail = subprocess.run(["bash", "-lc", "tail -n 15 /opt/ai_gateway_%s.log" % NAME],
                          stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore")
    print("--- 日志末尾 ---\n" + tail)

# 4) 经专用网关用 Anthropic 格式真测一次
def try_msg(auth):
    body = json.dumps({"model": MODEL, "max_tokens": 128,
                       "messages": [{"role": "user", "content": "回一个字:好"}]}).encode()
    h = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
    h.update(auth)
    req = urllib.request.Request("http://127.0.0.1:%s/v1/messages" % PORT, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

ok = False
if listening:
    for auth in ({"x-api-key": TOKEN}, {"Authorization": "Bearer " + TOKEN}):
        try:
            j = try_msg(auth)
            txt = "".join(b.get("text", "") for b in (j.get("content") or []) if isinstance(b, dict))
            if j.get("content"):
                print("✓ 经 %s 测 %s 成功,回复: %s" % (PORT, MODEL, (txt or "有结构化回复")[:50]))
                ok = True
                break
        except urllib.error.HTTPError as e:
            print("  (%s: %s)" % (list(auth)[0], e.code))
        except Exception as e:
            print("  (试了下:", str(e)[:80], ")")
if listening and not ok:
    print("[!] 端口起来了但测试没过,命令仍给你,先试;不行发老板看日志。")

# 5) 专用配置目录 + 启动命令
cfg = "/opt/claude-%s-cfg" % NAME
os.makedirs(cfg, exist_ok=True)
json.dump({"env": {"ANTHROPIC_BASE_URL": "http://127.0.0.1:%s" % PORT,
                   "ANTHROPIC_AUTH_TOKEN": TOKEN, "ANTHROPIC_MODEL": MODEL}},
          open(os.path.join(cfg, "settings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
launcher = ("#!/bin/bash\n"
            "# 用 %s 跑 Claude Code(专用通道 %s),不影响普通 claude(主号)\n"
            "export CLAUDE_CONFIG_DIR=%s\n"
            "export ANTHROPIC_BASE_URL=http://127.0.0.1:%s\n"
            "export ANTHROPIC_AUTH_TOKEN=%s\n"
            'export ANTHROPIC_MODEL="%s"\n'
            'exec claude "$@"\n') % (MODEL, PORT, cfg, PORT, TOKEN, MODEL)
lp = "/usr/local/bin/%s" % NAME
open(lp, "w").write(launcher)
os.chmod(lp, 0o755)

print("\n=========== 完成 ===========")
print("用 %s 跑 Claude Code,直接敲:  %s" % (MODEL, NAME))
print("用回主号(opus),照常敲:        claude")
print("专用网关日志: /opt/ai_gateway_%s.log" % NAME)
print("想关掉这个通道: pkill -f ai_gateway_%s.py" % NAME)
