#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读体检: 看 AI 网关/池子/Claude Code 现在怎么配的(key 自动打码,贴出来安全)。
不改任何东西。用法: python3 code_ai_status.py"""
import os, re, glob, json, subprocess


def mask(s):
    s = str(s or "")
    return s if len(s) < 12 else s[:6] + "…" + s[-4:]


print("======== 1. 网关脚本 ========")
gw = None
for p in ["/opt/ai_gateway.py", "/root/ai_gateway.py"] + glob.glob("/opt/**/ai_gateway.py", recursive=True):
    if os.path.isfile(p):
        gw = p
        print("找到网关:", p)
        break
if not gw:
    print("没找到 ai_gateway.py(网关可能没装或换端时丢了)")

print("\n======== 2. 池子配置(key 打码) ========")
pool = None
for p in ["/opt/ai_pool.json", "/root/ai_pool.json", "/root/.ai_pool.json"] + glob.glob("/opt/**/ai_pool.json", recursive=True):
    if os.path.isfile(p):
        pool = p
        break
if pool:
    print("找到池子:", pool)
    try:
        d = json.load(open(pool, encoding="utf-8"))
        items = d if isinstance(d, list) else (d.get("keys") or d.get("accounts") or d.get("pool") or [])
        print("池子里有 %d 个号:" % len(items))
        for i, it in enumerate(items):
            if isinstance(it, dict):
                shown = {k: (mask(v) if "key" in k.lower() or "token" in k.lower() else v) for k, v in it.items()}
                print("  [%d] %s" % (i, json.dumps(shown, ensure_ascii=False)))
            else:
                print("  [%d] %s" % (i, mask(it)))
    except Exception as e:
        print("池子读不动:", str(e)[:150])
else:
    print("没找到 ai_pool.json")

print("\n======== 3. 网关在跑吗 ========")
ps = subprocess.run(["bash", "-lc", "ps aux | grep -E 'ai_gateway|gateway' | grep -v grep"],
                    stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print(ps if ps else "网关进程没在跑")
print("--- screen 会话 ---")
sc = subprocess.run(["bash", "-lc", "screen -ls 2>/dev/null"], stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print(sc if sc else "无 screen")

print("\n======== 4. Claude Code 现在指向哪 ========")
sf = os.path.expanduser("~/.claude/settings.json")
if os.path.isfile(sf):
    try:
        e = (json.load(open(sf, encoding="utf-8")) or {}).get("env", {})
        print("settings.json env:")
        print("  BASE_URL =", e.get("ANTHROPIC_BASE_URL"))
        print("  TOKEN    =", mask(e.get("ANTHROPIC_AUTH_TOKEN")))
        print("  MODEL    =", e.get("ANTHROPIC_MODEL"))
    except Exception as ex:
        print("settings.json 读不动:", str(ex)[:120])
else:
    print("没有 ~/.claude/settings.json")
# 别名/包装器
al = subprocess.run(["bash", "-lc", "grep -rhnE 'ANTHROPIC_BASE_URL|ANTHROPIC_MODEL|claude' ~/.bashrc ~/.profile ~/.zshrc 2>/dev/null | grep -iv '#' | head"],
                    stdout=subprocess.PIPE).stdout.decode("utf-8", "ignore").strip()
print("--- 启动配置里的相关行 ---")
print(al if al else "无")
print("\n== 体检完,把上面全部发老婆 ==")
