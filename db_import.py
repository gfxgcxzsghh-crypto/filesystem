#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一个 .sql 导入 FiveM 数据库(自动读 cfg 连接串, 不回显密码)
用法: python3 db_import.py /path/to/xxx.sql  [服务端目录(默认 /opt/jiutian_new)]
⚠️ 会覆盖同名表的数据, 导入前请确认已备份!
"""
import re, os, subprocess, glob, sys

if len(sys.argv) < 2:
    print("[X] 用法: python3 db_import.py 要导入的.sql文件路径")
    raise SystemExit(1)

sql_file = sys.argv[1]
ROOT = sys.argv[2] if len(sys.argv) > 2 else "/opt/jiutian_new"

if not os.path.isfile(sql_file):
    print("[X] 找不到 sql 文件:", sql_file)
    raise SystemExit(1)

cfgs = glob.glob(os.path.join(ROOT, "**", "*.cfg"), recursive=True)
conn = None
for c in cfgs:
    try:
        t = open(c, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    m = re.search(r'mysql_connection_string\s+"([^"]+)"', t) or re.search(r"mysql_connection_string\s+'([^']+)'", t)
    if m:
        conn = m.group(1)
        break

if not conn:
    print("[X] 没在 cfg 里找到 mysql_connection_string,把这句发老板。")
    raise SystemExit(1)

user = pw = host = db = None
port = "3306"
m = re.match(r'mysql://([^:]+):([^@]*)@([^:/]+)(?::(\d+))?/([^?]+)', conn)
if m:
    user, pw, host, prt, db = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    if prt:
        port = prt
else:
    d = {}
    for part in conn.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[k.strip().lower()] = v.strip()
    user = d.get("user") or d.get("uid") or d.get("userid") or "root"
    pw = d.get("password") or d.get("pwd") or ""
    host = d.get("server") or d.get("host") or "localhost"
    db = d.get("database") or d.get("initial catalog")
    port = d.get("port", port)

print("将导入到 => 库:%s  用户:%s  主机:%s:%s  (密码已隐藏)" % (db, user, host, port))
print("导入文件:", sql_file, "(%.1f MB)" % (os.path.getsize(sql_file) / 1e6))
if not db:
    print("[X] 没解析出数据库名,把这句发老板。")
    raise SystemExit(1)

cmd = ["mysql", "-h", host, "-P", str(port), "-u", user, "-p" + pw,
       "--default-character-set=utf8mb4", db]
try:
    with open(sql_file, "rb") as f:
        r = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE)
    if r.returncode == 0:
        print("==导入完成== 已写入数据库", db)
    else:
        err = r.stderr.decode("utf-8", "ignore")[:300]
        print("[X] 导入失败:", err)
        print("    把这段发老板。")
except FileNotFoundError:
    print("[X] 这台机器没装 mysql 客户端。数据库可能在 docker 里,把这句发老板。")
