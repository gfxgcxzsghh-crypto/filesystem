#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修 oxmysql 连不上数据库的 Error 1698 (root@localhost Access denied)。
根因: MariaDB 把 TCP 的 127.0.0.1 反向解析成 localhost,撞上免密的 root@localhost,
     导致带密码的连接被拒。修法: 开 skip-name-resolve,让 127.0.0.1 按 IP 认账号。
本脚本只做三件事,绝不导入/删除任何数据、不碰玩家档:
  1) 用本机 root socket 把连接串里的账号(127.0.0.1 / %)密码重新对一遍(幂等,双保险)
  2) 给 MariaDB 加 skip-name-resolve(幂等)
  3) 重启 MariaDB,并用 TCP+密码当场验证能否连上
用法: python3 db_fix_oxmysql.py [服务端目录=/opt/jiutian_new]
需 root 运行。"""
import re, os, glob, subprocess, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/opt/jiutian_new"

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
    host = d.get("server") or d.get("host") or "127.0.0.1"
    db = d.get("database")
    port = d.get("port", port)
print("解析结果 => 库:%s  用户:%s  主机:%s:%s  (密码已隐藏)" % (db, user, host, port))


def esc(s):
    return (s or "").replace("\\", "\\\\").replace("'", "\\'")


u, p = esc(user), esc(pw)

# 3. 重新对账号密码(只 ALTER/CREATE 用户,不建库不导数据)
sql = ""
for h in ("127.0.0.1", "%"):
    sql += "CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED BY '%s';\n" % (u, h, p)
    sql += "ALTER USER '%s'@'%s' IDENTIFIED BY '%s';\n" % (u, h, p)
    if user == "root":
        sql += "GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' WITH GRANT OPTION;\n" % (u, h)
    else:
        sql += "GRANT ALL PRIVILEGES ON `%s`.* TO '%s'@'%s';\n" % (db, u, h)
sql += "FLUSH PRIVILEGES;\n"

r = subprocess.run(["mysql"], input=sql.encode(), stderr=subprocess.PIPE)
if r.returncode != 0:
    err = r.stderr.decode("utf-8", "ignore")
    print("[X] 对密码失败:", err[:400])
    if "Access denied" in err:
        print("    本机 root socket 免密被改过了,发老板。")
    sys.exit(1)
print("✓ 账号密码已对好(127.0.0.1 / %)")

# 4. 加 skip-name-resolve(找 MariaDB 的 conf.d 目录放 drop-in)
DROPIN_DIRS = [
    "/etc/mysql/mariadb.conf.d",
    "/etc/mysql/conf.d",
    "/etc/my.cnf.d",
]
target = None
for dpath in DROPIN_DIRS:
    if os.path.isdir(dpath):
        target = os.path.join(dpath, "99-skip-name-resolve.cnf")
        break
if target:
    open(target, "w").write("[mysqld]\nskip-name-resolve\n")
    print("✓ 已写入", target)
else:
    # 兜底: 追加到 /etc/my.cnf
    cnf = "/etc/my.cnf"
    body = ""
    if os.path.isfile(cnf):
        body = open(cnf, encoding="utf-8", errors="ignore").read()
    if "skip-name-resolve" not in body:
        if "[mysqld]" in body:
            body = body.replace("[mysqld]", "[mysqld]\nskip-name-resolve", 1)
        else:
            body += "\n[mysqld]\nskip-name-resolve\n"
        open(cnf, "w").write(body)
    print("✓ 已在", cnf, "启用 skip-name-resolve")

# 5. 重启 MariaDB
print("正在重启 MariaDB ...")
restarted = False
for cmd in (["systemctl", "restart", "mariadb"], ["systemctl", "restart", "mysql"],
            ["service", "mariadb", "restart"], ["service", "mysql", "restart"]):
    rr = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if rr.returncode == 0:
        restarted = True
        print("✓ 已重启 (%s)" % " ".join(cmd))
        break
if not restarted:
    print("[!] 自动重启没成功,请手动: systemctl restart mariadb  然后再验证")

# 6. 当场验证: TCP + 密码 能不能连上
print("验证 TCP+密码 连接 ...")
test = subprocess.run(
    ["mysql", "-h", "127.0.0.1", "-P", str(port), "-u", user,
     "-p" + pw, "-e", "SELECT 1;"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if test.returncode == 0:
    print("==修好了== oxmysql 现在能用 127.0.0.1+密码 连上数据库了。")
    print("下一步: 去 txAdmin 重启服务器,再看控制台还有没有 Error 1698。")
else:
    print("[X] 还是连不上:", test.stderr.decode("utf-8", "ignore")[:400])
    print("    把这段发老板。")
