#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FiveM 资源后门扫描器  (纯 Python3 stdlib, 只读不改)
用法:
  python3 fivem_scan.py                      # 扫默认 /opt/jiutian_new/resources
  python3 fivem_scan.py /path/to/resources   # 扫指定目录
  python3 fivem_scan.py /path --min high      # 只看高危
作用: 静态扫描 lua/js 文件里常见的后门/混淆/外传/提权特征, 给风险清单。
注意: 这是"提示可疑", 不是"确诊有毒"。命中项需人工看一眼上下文。
"""
import os, re, sys, base64

DEFAULT_DIR = "/opt/jiutian_new/resources"
SEV = {"HIGH": ("🔴", 3), "MED": ("🟠", 2), "LOW": ("🟡", 1)}

# (正则, 级别, 说明)  —— re.I 忽略大小写
RULES = [
    (r"\b(loadstring|load)\s*\(", "HIGH", "动态执行代码(loadstring/load) — 后门最常用"),
    (r"assert\s*\(\s*load", "HIGH", "assert(load(...)) — 典型远程执行外壳"),
    (r"os\.execute|io\.popen", "HIGH", "调用系统命令(os.execute/io.popen)"),
    (r"discord(?:app)?\.com/api/webhooks", "HIGH", "Discord webhook — 常用于偷偷外传数据"),
    (r"from\s+base64|base64\.decode|FromBase64|atob\s*\(", "HIGH", "base64 解码 — 常配合藏代码"),
    (r"(?:\\x[0-9a-fA-F]{2}){6,}", "HIGH", "大段 \\x 十六进制转义 — 混淆藏代码"),
    (r"(?:string\.char\s*\(\s*\d+\s*,\s*\d+){3,}", "HIGH", "string.char 大量拼接 — 混淆字符串"),
    (r"PerformHttpRequest\s*\(", "MED", "发起 HTTP 请求 — 看目标是不是外部/可疑站"),
    (r"https?://(?:pastebin\.com|bit\.ly|tinyurl|raw\.githubusercontent|paste\.ee|hastebin)", "MED", "可疑外链(pastebin/短链/raw)"),
    (r"\b(?:AddAce|add_principal|add_ace)\b", "MED", "改 ACE 权限/管理员 — 看是不是偷偷提权"),
    (r"(?:ExecuteCommand|RunCommand)\s*\(", "MED", "服务端执行命令 — 看参数是不是可控"),
    (r"\bSetResourceKvp|GetResourceKvp\b.*(?:token|key|password|secret)", "MED", "读写敏感KV(token/密码)"),
    (r"\b(\d{1,3}\.){3}\d{1,3}\b", "LOW", "硬编码 IP 地址"),
    (r"eval\s*\(", "MED", "js eval() — 动态执行"),
    (r"(?:child_process|exec\s*\(|spawn\s*\()", "MED", "js 子进程/exec — 系统命令"),
]
COMPILED = [(re.compile(p, re.I), s, d) for p, s, d in RULES]

# 白名单域名(常见正规服务, 命中 PerformHttpRequest/外链时降噪)
SAFE_HOSTS = ("cfx.re", "fivem.net", "nui://", "cdn.jsdelivr", "fonts.googleapis")

EXTS = (".lua", ".js", ".net.js", ".mjs")
SKIP_DIRS = {".git", "node_modules", "cache"}

def scan_file(path):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return hits
    lines = text.splitlines()
    # 单行超长(压缩混淆)
    for i, ln in enumerate(lines, 1):
        if len(ln) > 2000:
            hits.append(("MED", i, "超长单行(>2000字符) — 可能是压缩/混淆代码", ln[:60]))
    for rx, sev, desc in COMPILED:
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            snippet = lines[line_no-1].strip()[:80] if line_no-1 < len(lines) else ""
            if sev != "HIGH" and any(h in snippet.lower() for h in SAFE_HOSTS):
                continue
            hits.append((sev, line_no, desc, snippet))
    return hits

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else DEFAULT_DIR
    min_sev = 1
    if "--min" in sys.argv:
        v = sys.argv[sys.argv.index("--min")+1].upper()
        min_sev = SEV.get(v, ("", 1))[1]
    if not os.path.isdir(root):
        print(f"❌ 目录不存在: {root}")
        sys.exit(1)

    print(f"🔍 扫描目录: {root}\n{'='*60}")
    total_files = 0
    flagged = {}  # resource -> list of (sev, file, line, desc, snippet)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(EXTS):
                continue
            total_files += 1
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root)
            res = rel.split(os.sep)[0]
            for sev, line, desc, snip in scan_file(fp):
                if SEV[sev][1] < min_sev:
                    continue
                flagged.setdefault(res, []).append((sev, rel, line, desc, snip))

    if not flagged:
        print(f"✅ 扫了 {total_files} 个文件, 没发现明显可疑特征。")
        print("(注:静态扫描不是100%,来路不明的资源仍建议谨慎)")
        return

    # 按资源里最高危程度排序
    def res_score(items):
        return max(SEV[s][1] for s,*_ in items)
    order = sorted(flagged.items(), key=lambda kv: (-res_score(kv[1]), kv[0]))

    hi = med = low = 0
    for res, items in order:
        items.sort(key=lambda x: -SEV[x[0]][1])
        top = SEV[items[0][0]][0]
        print(f"\n{top} 资源 [{res}]  ({len(items)} 处可疑)")
        seen = set()
        for sev, rel, line, desc, snip in items[:12]:
            icon = SEV[sev][0]
            key = (desc, rel)
            if key in seen:
                continue
            seen.add(key)
            print(f"   {icon} {rel}:{line}")
            print(f"      {desc}")
            if snip:
                print(f"      > {snip}")
            if sev == "HIGH": hi += 1
            elif sev == "MED": med += 1
            else: low += 1
        if len(items) > 12:
            print(f"   ... 还有 {len(items)-12} 处(同类居多)")

    print(f"\n{'='*60}")
    print(f"📊 汇总: 扫了 {total_files} 文件 | 🔴高危 {hi}  🟠中 {med}  🟡低 {low}")
    print("提示: 🔴 项务必人工看上下文;正规资源也可能用 PerformHttpRequest/IP,别一刀切。")
    print("最危险信号: loadstring/load + base64/\\x 混淆 同时出现 → 高度疑似后门。")

if __name__ == "__main__":
    main()
