#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夸克网盘 -> 服务器直下(用你自己的登录 cookie,拿自己网盘里的文件)。
cookie 放在 /opt/quark_cookie.txt(用 Cookie-Editor 从 pan.quark.cn 导出的 Header String)。
用法:
  python3 quark_dl.py [关键词]          # 搜自己网盘,列出文件+fid(默认关键词 ESX)
  python3 quark_dl.py <fid> "文件名"    # 下载指定文件到 /opt
"""
import json, os, sys, subprocess, urllib.request, urllib.parse

CK_FILE = "/opt/quark_cookie.txt"
if not os.path.isfile(CK_FILE):
    print("[X] 没有 cookie 文件 %s" % CK_FILE)
    print("    用宝塔在 /opt 新建 quark_cookie.txt,把 Cookie-Editor 导出的 cookie 粘进去保存。")
    sys.exit(1)


def build_cookie(raw):
    """兼容三种导出格式: Header String / JSON(As JSON) / Netscape(As Netscape)。
    只挑出夸克相关域名的 cookie,拼成 'name=value; ...' 的 Cookie 头。"""
    raw = raw.strip()

    def wanted(dom):
        dom = (dom or "").lower()
        return ("quark" in dom) or ("sm.cn" in dom)

    # JSON 导出(cookie 对象数组)
    if raw[:1] in ("[", "{"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                obj = obj.get("cookies") or obj.get("data") or []
            hit = ["%s=%s" % (c.get("name"), c.get("value"))
                   for c in obj if isinstance(c, dict) and wanted(c.get("domain"))]
            if hit:
                return "; ".join(hit)
            allp = ["%s=%s" % (c.get("name"), c.get("value"))
                    for c in obj if isinstance(c, dict) and c.get("name")]
            if allp:
                return "; ".join(allp)
        except Exception:
            pass
    # Netscape 导出(制表符分隔,每行 7 段)
    if "\t" in raw:
        hit = []
        for line in raw.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            p = line.split("\t")
            if len(p) >= 7 and wanted(p[0]):
                hit.append("%s=%s" % (p[5], p[6]))
        if hit:
            return "; ".join(hit)
    # 已经是 Header String(name=value; ...)
    return " ".join(raw.split())


COOKIE = build_cookie(open(CK_FILE, encoding="utf-8", errors="ignore").read())
if len(COOKIE) < 20 or "=" not in COOKIE:
    print("[X] 没从文件里挑出有效的夸克 cookie。确认导的是登录状态、且选了 As JSON/Netscape。")
    sys.exit(1)
print("已读取 cookie(%d 字符)" % len(COOKIE))

HDR = {
    "Cookie": COOKIE,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://pan.quark.cn/",
    "Origin": "https://pan.quark.cn",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}
BASE = "https://drive-pc.quark.cn/1/clouddrive"
COMMON = "pr=ucpro&fr=pc&uc_param_str="


import urllib.error


def _open(req):
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return json.loads(body)   # 夸克即使 400 也会返回 JSON 错误信息
        except Exception:
            return {"_http": e.code, "_raw": body[:500]}


def api_get(path):
    return _open(urllib.request.Request(BASE + path, headers=HDR))


def api_post(path, body):
    data = json.dumps(body).encode()
    return _open(urllib.request.Request(BASE + path, data=data, headers=HDR, method="POST"))


def human(n):
    n = n or 0
    for u in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return "%.2f%s" % (n, u)
        n /= 1024
    return "%.2fP" % n


# ---- 下载模式 ----
if len(sys.argv) >= 3:
    fid, name = sys.argv[1], sys.argv[2]
    print("拿下载地址中 ...")
    r = api_post("/file/download?%s" % COMMON, {"fids": [fid]})
    try:
        url = r["data"][0]["download_url"]
    except Exception:
        print("[X] 没拿到下载地址。夸克返回(截图发老板):")
        print(json.dumps(r, ensure_ascii=False)[:700])
        sys.exit(1)
    print("✓ 地址已拿到,开始下载 -> /opt/%s" % name)
    # 装 aria2(多线程,快);没有就用 wget
    if subprocess.run(["which", "aria2c"], stdout=subprocess.DEVNULL).returncode != 0:
        print("装 aria2 中 ...")
        subprocess.run(["apt-get", "install", "-y", "aria2"], stdout=subprocess.DEVNULL)
    if subprocess.run(["which", "aria2c"], stdout=subprocess.DEVNULL).returncode == 0:
        rc = subprocess.run([
            "aria2c", "-x16", "-s16", "-k1M", "--console-log-level=warn",
            "--header=Cookie: " + COOKIE,
            "--header=Referer: https://pan.quark.cn/",
            "-d", "/opt", "-o", name, url]).returncode
    else:
        rc = subprocess.run([
            "wget", "--header=Cookie: " + COOKIE,
            "--header=Referer: https://pan.quark.cn/",
            "-O", "/opt/" + name, url]).returncode
    if rc == 0 and os.path.isfile("/opt/" + name):
        print("\n==下载完成== /opt/%s (%s)" % (name, human(os.path.getsize("/opt/" + name))))
        print("下一步: 解压。zip -> unzip;  7z -> 7z x;  rar -> unrar x")
    else:
        print("[X] 下载没成功(rc=%s)。把上面的报错截图发老板。" % rc)
    sys.exit(0)

# ---- 搜索模式 ----
q = sys.argv[1] if len(sys.argv) > 1 else "ESX"
print("在你的夸克网盘里搜: %s\n" % q)
path = ("/file/search?%s&q=%s&_page=1&_size=50&_fetch_total=1"
        "&_sort=file_type:desc,updated_at:desc" % (COMMON, urllib.parse.quote(q)))
try:
    r = api_get(path)
except Exception as e:
    print("[X] 请求失败(多半是 cookie 过期/不对):", str(e)[:200])
    print("    重新用 Cookie-Editor 导出粘到 /opt/quark_cookie.txt 再试。")
    sys.exit(1)
items = (r.get("data") or {}).get("list") or []
if not items:
    print("没搜到 '%s'。换个词试试: python3 /opt/quark_dl.py 别的关键词" % q)
    print("(返回码:", r.get("code"), r.get("message"), ")")
    sys.exit(0)
print("找到这些(选那个【文件】、体积最大的那个整合包):\n")
for it in items:
    is_dir = it.get("dir") or it.get("file") is False
    typ = "📁文件夹" if is_dir else "📄文件"
    print("%s | %8s | %s" % (typ, human(it.get("size", 0)), it.get("file_name")))
    print("        fid = %s\n" % it.get("fid"))
print("=" * 40)
print("找到那个 21G 的【文件】,复制它的 fid,跑这条下载:")
print('  python3 /opt/quark_dl.py <fid> "ESX.zip"')
print("(文件名随便起,但后缀要对: 压缩包是 .zip/.7z/.rar 就写对应后缀)")
