#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 FiveM server.cfg 的连接串,在本机 MySQL/MariaDB 建库+建用户+导入数据(不回显密码)。
用法: python3 db_deploy.py [服务端目录=/opt/jiutian_new] [sql文件=/opt/db_backup_jiutian.sql]
需以 root 运行(建库用本机 root socket;导入用连接串里的账号密码走 TCP)。"""
import re, os, glob, subprocess, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/opt/jiutian_new"
SQL_FILE = sys.argv[2] if len(sys.argv) > 2 else "/opt/db_backup_jiutian.sql"

# 1. 找连接串
conn = None
for c in glob.glob(os.path.join(ROOT, "**", "*.cfg"), recursive=True):
    try:
        t = open(c, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    m = re.search(r'mysql_connection_string\s+"([^"]+)"', t) or re.search(r"mysql_connection_string\s+'([^']+)'", t)
    if m:
        conn = m.group(1)
        print("在", os.path.relpath(c, ROOT), "找到连接串")
        break
if not conn:
    print("[X] 没找到 mysql_connection_string,发老板。")
    sys.exit(1)

# 2. 解析
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
    user = d.get("user") or d.get("uid") or "root"
    pw = d.get("password") or d.get("pwd") or ""
    host = d.get("server") or d.get("host") or "localhost"
    db = d.get("database")
    port = d.get("port", port)
if not db:
    print("[X] 没解析出数据库名,发老板。")
    sys.exit(1)
if host in ("localhost", ""):
    host = "127.0.0.1"
print("解析结果 => 库:%s  用户:%s  主机:%s:%s  (密码已隐藏)" % (db, user, host, port))


def esc(s):
    return (s or "").replace("\\", "\\\\").replace("'", "\\'")


u, p = esc(user), esc(pw)

# 3. 建库 + 建用户(本机 root socket)
sql = "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n" % db
for h in ("localhost", "127.0.0.1", "%"):
    sql += "CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED BY '%s';\n" % (u, h, p)
    sql += "ALTER USER '%s'@'%s' IDENTIFIED BY '%s';\n" % (u, h, p)
    sql += "GRANT ALL PRIVILEGES ON `%s`.* TO '%s'@'%s';\n" % (db, u, h)
sql += "FLUSH PRIVILEGES;\n"

r = subprocess.run(["mysql"], input=sql.encode(), stderr=subprocess.PIPE)
if r.returncode != 0:
    err = r.stderr.decode("utf-8", "ignore")
    # 若 root socket 已被改成密码(重复跑本脚本时会这样),改用密码重试建库
    if "Access denied" in err:
        r2 = subprocess.run(["mysql", "-h", host, "-P", str(port), "-u", user, "-p" + pw],
                            input=sql.encode(), stderr=subprocess.PIPE)
        if r2.returncode != 0:
            print("[X] 建库/用户失败:", r2.stderr.decode("utf-8", "ignore")[:400])
            sys.exit(1)
    else:
        print("[X] 建库/用户失败:", err[:400])
        print("    (若提示 command not found,先装 mariadb-server;发老板。)")
        sys.exit(1)
print("✓ 数据库和用户已建好")

# 4. 导入数据 —— 用连接串里的账号密码走 TCP(user=root 时 socket 免密已失效)
if not os.path.isfile(SQL_FILE):
    print("[!] 没找到 sql 文件:", SQL_FILE, "— 跳过导入(数据库结构已建好)")
    sys.exit(0)
cmd = ["mysql", "-h", host, "-P", str(port), "-u", user, "-p" + pw, "--default-character-set=utf8mb4", db]
with open(SQL_FILE, "rb") as f:
    r = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE)
if r.returncode == 0:
    print("==导入完成== 数据已进库 %s" % db)
    print("下一步可以启动 FiveM 了。")
else:
    print("[X] 导入失败:", r.stderr.decode("utf-8", "ignore")[:400])
