#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FiveM 资源后门扫描器 · 专业图形版
双击打开窗口 -> 选资源文件夹 -> 扫描 -> 可导出 HTML 报告
静态扫描,只读不改。命中为"提示可疑",需人工复核上下文。
"""
import os, re, html, threading, webbrowser

# ========== 扫描核心 ==========
RULES = [
    ("load",   r"\b(loadstring|load)\s*\(",                         "HIGH", "动态执行代码(loadstring/load)"),
    ("assert", r"assert\s*\(\s*load",                               "HIGH", "assert(load(...)) 远程执行外壳"),
    ("os",     r"os\.execute|io\.popen",                            "HIGH", "调用系统命令(os.execute/io.popen)"),
    ("hook",   r"discord(?:app)?\.com/api/webhooks",                "HIGH", "Discord webhook 外传数据"),
    ("b64",    r"from\s+base64|base64\.decode|FromBase64|atob\s*\(", "HIGH", "base64 解码(常配合藏代码)"),
    ("hex",    r"(?:\\x[0-9a-fA-F]{2}){6,}",                        "HIGH", "大段 \\x 十六进制混淆"),
    ("char",   r"(?:string\.char\s*\(\s*\d+\s*,\s*\d+){3,}",        "HIGH", "string.char 拼接混淆"),
    ("http",   r"PerformHttpRequest\s*\(",                          "MED",  "发起 HTTP 请求(看目标)"),
    ("url",    r"https?://(?:pastebin\.com|bit\.ly|tinyurl|raw\.githubusercontent|paste\.ee|hastebin)", "MED", "可疑外链"),
    ("ace",    r"\b(?:AddAce|add_principal|add_ace)\b",             "MED",  "改 ACE 权限/管理员"),
    ("cmd",    r"(?:ExecuteCommand|RunCommand)\s*\(",               "MED",  "服务端执行命令"),
    ("eval",   r"eval\s*\(",                                        "MED",  "js eval() 动态执行"),
    ("proc",   r"(?:child_process|exec\s*\(|spawn\s*\()",           "MED",  "js 子进程/exec"),
    ("ip",     r"\b(\d{1,3}\.){3}\d{1,3}\b",                        "LOW",  "硬编码 IP"),
]
COMPILED = [(t, re.compile(p, re.I), s, d) for t, p, s, d in RULES]
SAFE = ("cfx.re", "fivem.net", "nui://", "cdn.jsdelivr", "fonts.googleapis")
EXTS = (".lua", ".js", ".mjs")
SKIP = {".git", "node_modules", "cache", ".vscode"}
LEVEL = {"CRIT": 4, "HIGH": 3, "MED": 2, "LOW": 1}
LVNAME = {4: "CRIT", 3: "HIGH", 2: "MED", 1: "LOW"}

def scan_file(path):
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return []
    lines = text.splitlines()
    hits, tags = [], set()
    for i, ln in enumerate(lines, 1):
        if len(ln) > 2000:
            hits.append(("MED", i, "超长单行(压缩/混淆可能)", ln[:70]))
    for tag, rx, sev, desc in COMPILED:
        for m in rx.finditer(text):
            n = text.count("\n", 0, m.start()) + 1
            snip = lines[n - 1].strip()[:90] if n - 1 < len(lines) else ""
            if sev != "HIGH" and any(h in snip.lower() for h in SAFE):
                continue
            hits.append((sev, n, desc, snip))
            tags.add(tag)
    if ("load" in tags or "assert" in tags) and (tags & {"b64", "hex", "char"}):
        hits.insert(0, ("CRIT", 0, "★ 严重疑似后门:同文件『动态执行』+『混淆/base64』组合出现 ★", ""))
    return hits

def scan_dir(root, progress=None):
    total = 0
    flagged = {}
    allf = []
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP]
        for fn in fns:
            if fn.endswith(EXTS):
                allf.append(os.path.join(dp, fn))
    for idx, fp in enumerate(allf):
        total += 1
        rel = os.path.relpath(fp, root)
        res = rel.split(os.sep)[0]
        for h in scan_file(fp):
            flagged.setdefault(res, []).append((h[0], rel, h[1], h[2], h[3]))
        if progress:
            progress(idx + 1, len(allf))
    return total, flagged

def res_max(items):
    return max(LEVEL[s] for s, *_ in items)

# ========== HTML 报告 ==========
def build_html(root, total, flagged):
    color = {"CRIT": "#f85149", "HIGH": "#ff9d5c", "MED": "#d9b23a", "LOW": "#7d8aa8"}
    order = sorted(flagged.items(), key=lambda kv: (-res_max(kv[1]), kv[0]))
    cards = []
    hi = med = low = crit = 0
    for res, items in order:
        items.sort(key=lambda x: -LEVEL[x[0]])
        rows = []
        seen = set()
        for sev, rel, ln, desc, snip in items:
            if (desc, rel, ln) in seen:
                continue
            seen.add((desc, rel, ln))
            if sev == "CRIT": crit += 1
            elif sev == "HIGH": hi += 1
            elif sev == "MED": med += 1
            else: low += 1
            loc = html.escape("%s:%d" % (rel, ln)) if ln else html.escape(rel)
            sn = ("<div class='sn'>&gt; %s</div>" % html.escape(snip)) if snip else ""
            rows.append("<div class='row' style='border-left:4px solid %s'><b style='color:%s'>[%s]</b> %s<div class='d'>%s</div>%s</div>"
                        % (color[sev], color[sev], sev, loc, html.escape(desc), sn))
        top = LVNAME[res_max(items)]
        cards.append("<div class='card'><h3 style='color:%s'>资源 [%s] · %d 处可疑 · 最高 %s</h3>%s</div>"
                     % (color[top], html.escape(res), len(items), top, "".join(rows)))
    body = "".join(cards) if cards else "<div class='card'><h3 style='color:#3fb950'>✅ 未发现明显可疑特征</h3></div>"
    return """<!doctype html><html><head><meta charset="utf-8"><title>FiveM 后门扫描报告</title>
<style>body{background:#0f1420;color:#c9d3e6;font-family:'Segoe UI','Microsoft YaHei',sans-serif;margin:0;padding:24px}
h1{color:#e8eefc}h3{margin:0 0 10px}.top{background:#151c2c;padding:16px 20px;border-radius:10px;margin-bottom:18px}
.card{background:#141b29;border:1px solid #2a3550;border-radius:10px;padding:14px 18px;margin-bottom:14px}
.row{background:#0f1420;padding:8px 12px;border-radius:6px;margin:8px 0}.d{color:#9fb0cc;font-size:13px;margin-top:3px}
.sn{color:#6b7791;font-family:monospace;font-size:12px;margin-top:4px;word-break:break-all}
.st{display:inline-block;margin-right:20px;font-size:15px}</style></head><body>
<div class="top"><h1>FiveM 资源后门扫描报告</h1>
<div>扫描目录: %s ｜ 文件数: %d</div>
<div style="margin-top:8px">
<span class="st" style="color:#f85149">严重 %d</span>
<span class="st" style="color:#ff9d5c">高危 %d</span>
<span class="st" style="color:#d9b23a">中 %d</span>
<span class="st" style="color:#7d8aa8">低 %d</span></div>
<div style="color:#6b7791;font-size:12px;margin-top:8px">提示: 静态扫描为"提示可疑",非确诊。严重/高危项务必人工看上下文;正规资源也会用 HTTP/IP。</div></div>
%s</body></html>""" % (html.escape(root), total, crit, hi, med, low, body)

# ========== 图形界面 ==========
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    state = {"root": "", "report": ""}
    win = tk.Tk()
    win.title("FiveM 资源后门扫描器")
    win.geometry("760x560")
    win.configure(bg="#0f1420")

    tk.Label(win, text="FiveM 资源后门扫描器", fg="#e8eefc", bg="#0f1420",
             font=("Microsoft YaHei", 16, "bold")).pack(pady=(14, 4))
    tk.Label(win, text="选择 FiveM 资源文件夹 → 扫描 → 可导出 HTML 报告(静态扫描,只读)",
             fg="#7d8aa8", bg="#0f1420", font=("Microsoft YaHei", 9)).pack()

    pathvar = tk.StringVar(value="未选择文件夹")
    frm = tk.Frame(win, bg="#0f1420"); frm.pack(pady=10, fill="x", padx=20)
    tk.Label(frm, textvariable=pathvar, fg="#9fb0cc", bg="#141b29", anchor="w",
             font=("Consolas", 9)).pack(side="left", fill="x", expand=True, ipady=6, ipadx=8)

    txt = tk.Text(win, bg="#0f1420", fg="#c9d3e6", font=("Consolas", 10),
                  insertbackground="#c9d3e6", wrap="word", relief="flat")
    txt.pack(fill="both", expand=True, padx=20, pady=6)
    txt.tag_config("CRIT", foreground="#f85149", font=("Consolas", 10, "bold"))
    txt.tag_config("HIGH", foreground="#ff9d5c")
    txt.tag_config("MED", foreground="#d9b23a")
    txt.tag_config("LOW", foreground="#7d8aa8")
    txt.tag_config("head", foreground="#e8eefc", font=("Consolas", 11, "bold"))
    txt.tag_config("ok", foreground="#3fb950")

    def choose():
        d = filedialog.askdirectory(title="选择 FiveM 资源文件夹")
        if d:
            state["root"] = d
            pathvar.set(d)

    def do_scan():
        if not state["root"]:
            messagebox.showwarning("提示", "请先选择资源文件夹")
            return
        txt.delete("1.0", "end")
        txt.insert("end", "扫描中,请稍候...\n", "head")
        win.update()

        def worker():
            total, flagged = scan_dir(state["root"])
            state["report"] = build_html(state["root"], total, flagged)
            win.after(0, lambda: show(total, flagged))

        threading.Thread(target=worker, daemon=True).start()

    def show(total, flagged):
        txt.delete("1.0", "end")
        if not flagged:
            txt.insert("end", "✅ 扫了 %d 个文件,未发现明显可疑特征。\n" % total, "ok")
        else:
            order = sorted(flagged.items(), key=lambda kv: (-res_max(kv[1]), kv[0]))
            for res, items in order:
                items.sort(key=lambda x: -LEVEL[x[0]])
                top = LVNAME[res_max(items)]
                txt.insert("end", "\n[%s] 资源 %s  (%d 处)\n" % (top, res, len(items)), "head")
                seen = set()
                for sev, rel, ln, desc, snip in items[:15]:
                    if (desc, rel, ln) in seen: continue
                    seen.add((desc, rel, ln))
                    loc = "%s:%d" % (rel, ln) if ln else rel
                    txt.insert("end", "   [%s] %s\n        %s\n" % (sev, loc, desc), sev)
        txt.insert("end", "\n" + "=" * 50 + "\n扫描完成。点『导出HTML报告』生成可分享的报告。\n", "head")

    def export():
        if not state["report"]:
            messagebox.showwarning("提示", "请先扫描")
            return
        f = filedialog.asksaveasfilename(defaultextension=".html",
                                         initialfile="FiveM扫描报告.html",
                                         filetypes=[("HTML", "*.html")])
        if f:
            open(f, "w", encoding="utf-8").write(state["report"])
            webbrowser.open("file://" + os.path.abspath(f))

    btns = tk.Frame(win, bg="#0f1420"); btns.pack(pady=12)

    def mkbtn(t, cmd, bg):
        return tk.Button(btns, text=t, command=cmd, bg=bg, fg="white", relief="flat",
                         font=("Microsoft YaHei", 10, "bold"), padx=18, pady=8, cursor="hand2")
    mkbtn("① 选择文件夹", choose, "#3a4a6a").pack(side="left", padx=6)
    mkbtn("② 开始扫描", do_scan, "#e8734f").pack(side="left", padx=6)
    mkbtn("③ 导出HTML报告", export, "#3a6a4a").pack(side="left", padx=6)

    win.mainloop()

if __name__ == "__main__":
    try:
        run_gui()
    except Exception:
        # 没有图形环境时,退回命令行
        import sys
        root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
        total, flagged = scan_dir(root)
        print("扫描 %s: %d 文件" % (root, total))
        for res, items in sorted(flagged.items(), key=lambda kv: -res_max(kv[1])):
            print("[%s] %s: %d处" % (LVNAME[res_max(items)], res, len(items)))
