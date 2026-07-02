#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FiveM 资源后门扫描器 · 电脑版(Windows 友好, 拖文件夹进来即可扫)"""
import os, re, sys, io

# Windows 控制台 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SEV = {"HIGH": ("[!!! 高危]", 3), "MED": ("[!! 中 ]", 2), "LOW": ("[!  低 ]", 1)}
RULES = [
    (r"\b(loadstring|load)\s*\(", "HIGH", "动态执行代码(loadstring/load) - 后门最常用"),
    (r"assert\s*\(\s*load", "HIGH", "assert(load(...)) - 典型远程执行外壳"),
    (r"os\.execute|io\.popen", "HIGH", "调用系统命令(os.execute/io.popen)"),
    (r"discord(?:app)?\.com/api/webhooks", "HIGH", "Discord webhook - 常用于偷偷外传数据"),
    (r"from\s+base64|base64\.decode|FromBase64|atob\s*\(", "HIGH", "base64 解码 - 常配合藏代码"),
    (r"(?:\\x[0-9a-fA-F]{2}){6,}", "HIGH", "大段 \\x 十六进制转义 - 混淆藏代码"),
    (r"(?:string\.char\s*\(\s*\d+\s*,\s*\d+){3,}", "HIGH", "string.char 大量拼接 - 混淆字符串"),
    (r"PerformHttpRequest\s*\(", "MED", "发起 HTTP 请求 - 看目标是不是外部/可疑站"),
    (r"https?://(?:pastebin\.com|bit\.ly|tinyurl|raw\.githubusercontent|paste\.ee|hastebin)", "MED", "可疑外链(pastebin/短链/raw)"),
    (r"\b(?:AddAce|add_principal|add_ace)\b", "MED", "改 ACE 权限/管理员 - 看是不是偷偷提权"),
    (r"(?:ExecuteCommand|RunCommand)\s*\(", "MED", "服务端执行命令 - 看参数是不是可控"),
    (r"\b(\d{1,3}\.){3}\d{1,3}\b", "LOW", "硬编码 IP 地址"),
    (r"eval\s*\(", "MED", "js eval() - 动态执行"),
    (r"(?:child_process|exec\s*\(|spawn\s*\()", "MED", "js 子进程/exec - 系统命令"),
]
COMPILED = [(re.compile(p, re.I), s, d) for p, s, d in RULES]
SAFE_HOSTS = ("cfx.re", "fivem.net", "nui://", "cdn.jsdelivr", "fonts.googleapis")
EXTS = (".lua", ".js", ".mjs")
SKIP_DIRS = {".git", "node_modules", "cache"}
OUT = []
def emit(s):
    print(s); OUT.append(s)

def scan_file(path):
    hits = []
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return hits
    lines = text.splitlines()
    for i, ln in enumerate(lines, 1):
        if len(ln) > 2000:
            hits.append(("MED", i, "超长单行(>2000字符) - 可能是压缩/混淆代码", ln[:60]))
    for rx, sev, desc in COMPILED:
        for m in rx.finditer(text):
            n = text.count("\n", 0, m.start()) + 1
            snip = lines[n-1].strip()[:80] if n-1 < len(lines) else ""
            if sev != "HIGH" and any(h in snip.lower() for h in SAFE_HOSTS):
                continue
            hits.append((sev, n, desc, snip))
    return hits

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else os.getcwd()
    if not os.path.isdir(root):
        emit("[X] 目录不存在: " + root); return
    emit("扫描目录: " + root)
    emit("=" * 60)
    total = 0; flagged = {}
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for fn in fns:
            if not fn.endswith(EXTS): continue
            total += 1
            fp = os.path.join(dp, fn); rel = os.path.relpath(fp, root)
            res = rel.split(os.sep)[0]
            for sev, line, desc, snip in scan_file(fp):
                flagged.setdefault(res, []).append((sev, rel, line, desc, snip))
    if not flagged:
        emit("[OK] 扫了 %d 个文件, 没发现明显可疑特征。" % total)
    else:
        order = sorted(flagged.items(), key=lambda kv: (-max(SEV[s][1] for s,*_ in kv[1]), kv[0]))
        hi=med=low=0
        for res, items in order:
            items.sort(key=lambda x: -SEV[x[0]][1])
            emit("")
            emit("%s 资源 [%s]  (%d 处可疑)" % (SEV[items[0][0]][0], res, len(items)))
            seen=set()
            for sev, rel, line, desc, snip in items[:12]:
                k=(desc,rel)
                if k in seen: continue
                seen.add(k)
                emit("   %s %s:%d" % (SEV[sev][0], rel, line))
                emit("      " + desc)
                if snip: emit("      > " + snip)
                if sev=="HIGH": hi+=1
                elif sev=="MED": med+=1
                else: low+=1
            if len(items)>12: emit("   ... 还有 %d 处" % (len(items)-12))
        emit(""); emit("="*60)
        emit("汇总: 扫了 %d 文件 | 高危 %d  中 %d  低 %d" % (total, hi, med, low))
    emit("")
    emit("看结果心法: [高危] loadstring/load + base64/\\x 同时出现 = 高度疑似后门")
    emit("正规资源也会用 PerformHttpRequest/IP, 别一刀切, 点开那行看在干嘛")
    # 存报告
    try:
        rp = os.path.join(root, "扫描报告.txt")
        open(rp, "w", encoding="utf-8").write("\n".join(OUT))
        print("\n报告已保存: " + rp)
    except Exception:
        pass

if __name__ == "__main__":
    main()
    try:
        input("\n扫描结束, 按回车键关闭窗口...")
    except Exception:
        pass
