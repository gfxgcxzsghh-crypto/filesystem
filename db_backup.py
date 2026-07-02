#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动从 FiveM server.cfg 读取数据库连接串并 mysqldump 备份(不回显密码)"""
import re, os, subprocess, glob, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/opt/jiutian_new"

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
        print("在 %s 找到数据库连接串" % os.path.relpath(c, ROOT))
        break

if not conn:
    print("[X] 没在 cfg 里找到 mysql_connection_string。")
    print("    把这句发给老板,可能连接信息在别处或用了环境变量。")
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

print("解析结果 => 库:%s  用户:%s  主机:%s:%s  (密码已隐藏)" % (db, user, host, port))
if not db:
    print("[X] 没解析出数据库名,连接串格式特殊,把这句发老板。")
    raise SystemExit(1)

out = "/opt/db_backup_%s.sql" % db
cmd = ["mysqldump", "-h", host, "-P", str(port), "-u", user, "-p" + pw,
       "--single-transaction", "--default-character-set=utf8mb4", db]
try:
    with open(out, "wb") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
    if r.returncode == 0 and os.path.getsize(out) > 100:
        print("==数据库备份完成== %s  %.1f MB" % (out, os.path.getsize(out) / 1e6))
    else:
        err = r.stderr.decode("utf-8", "ignore")[:300]
        print("[X] mysqldump 失败:", err)
        print("    如果提示连不上,数据库可能在 docker 里;把这段发老板。")
except FileNotFoundError:
    print("[X] 这台机器没装 mysqldump。数据库可能在 docker 里,或要装 mysql-client。")
    print("    把这句发老板,我给 docker 里备份的办法。")
