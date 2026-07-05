#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 o站 gpt-4o 加到 AI 网关池子末尾(当兜底备用),然后重启网关。
- 复用池子里已有的 o站(omaleai) key,不需要手输任何密钥
- 只在末尾追加,绝不改动/删除已有的号
- 自动备份 ai_pool.json -> ai_pool.json.bak
用法: python3 add_gpt4o.py   (需 root)"""
import os, json, glob, shutil, subprocess, time, urllib.request, urllib.error

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
    print("[X] 池子不是数组格式(是 %s),别乱改,发老板。" % type(d).__name__)
    raise SystemExit(1)

# 1) 从已有的号里挑出 o站(omaleai) 的 key
o_key = None
for it in d:
    if isinstance(it, dict) and "omaleai" in str(it.get("base", "")):
        o_key = it.get("key")
        break
if not o_key:
    print("[X] 池子里没有 o站(omaleai) 的号,拿不到 key。发老板手动加。")
    raise SystemExit(1)
print("✓ 复用池子里的 o站 key: %s…%s" % (o_key[:6], o_key[-4:]))

BASE = "https://omaleai.qzz.io/v1"
NEW = {"base": BASE, "key": o_key, "model": "gpt-4o"}

# 2) 已经有 gpt-4o 就不重复加
if any(isinstance(it, dict) and it.get("model") == "gpt-4o" and "omaleai" in str(it.get("base", "")) for it in d):
    print("池子里已经有 gpt-4o 了,不重复加。")
else:
    shutil.copy(POOL, POOL + ".bak")
    print("✓ 已备份 ->", POOL + ".bak")
    d.append(NEW)  # 加末尾 = 兜底,前面号都挂了才用它
    json.dump(d, open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("✓ 已在池子末尾加上 gpt-4o(第 %d 个号)" % (len(d) - 1))

# 3) 先直连 o站 验证 gpt-4o 这个号确实能用(不经网关)
print("验证 o站 gpt-4o 直连能不能用 ...")
try:
    body = json.dumps({"model": "gpt-4o",
                       "messages": [{"role": "user", "content": "回一个字:好"}]}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body, method="POST", headers={
        "Authorization": "Bearer " + o_key, "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json", "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.loads(r.read().decode("utf-8", "ignore"))
    real = j.get("model", "?")
    print("✓ gpt-4o 真能用(实际返回: %s)" % real)
except Exception as e:
    print("[!] gpt-4o 直连验证没过(%s)——但已加进池子,当兜底不影响主号。" % str(e)[:120])

# 4) 重启网关(优先 systemd,否则 kill+nohup 原样拉起)
print("重启网关 ...")
svc = None
try:
    out = subprocess.run(["bash", "-lc", "systemctl list-units --type=service 2>/dev/null | grep -iE 'gateway|ai_gateway'"],
                         stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore")
    if out.strip():
        svc = out.split()[0]
except Exception:
    pass
if svc:
    subprocess.run(["systemctl", "restart", svc])
    print("✓ 已 systemctl restart", svc)
else:
    subprocess.run(["bash", "-lc", "pkill -f ai_gateway.py"])
    time.sleep(1.5)
    subprocess.run(["bash", "-lc",
                    "cd /opt && nohup python3 -u /opt/ai_gateway.py > /opt/ai_gateway.log 2>&1 &"])
    print("✓ 已重新拉起网关(日志: /opt/ai_gateway.log)")

# 5) 确认网关活着 + 端口在听
time.sleep(2)
alive = subprocess.run(["bash", "-lc", "ps aux | grep ai_gateway.py | grep -v grep"],
                       stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
port = subprocess.run(["bash", "-lc", "ss -ltnp 2>/dev/null | grep 8787 || netstat -ltnp 2>/dev/null | grep 8787"],
                      stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print("\n网关进程:", "活着 ✓" if alive else "没起来 ✗(看 /opt/ai_gateway.log)")
print("8787 端口:", "在听 ✓" if port else "没听到 ✗")
print("\n== 完成 == gpt-4o 已作兜底备用接进 Claude Code。")
print("以后前面 5 个 Claude 号都挂了,会自动用 gpt-4o,Claude Code 不断。")
print("想撤销: cp %s.bak %s 然后重启网关。" % (POOL, POOL))
