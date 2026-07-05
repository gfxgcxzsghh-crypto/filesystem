#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FiveM 成品端 · 全自动换端(给笨蛋管理员用)。
管理员只需:①把新端上传到 /opt/new_server ②跑这一条命令,回答几个 是/否。
脚本自动: 备份 → 扫后门 → 接线(把你这台的 license/数据库/端口搬到新端) → 换 resources → 可选导库 → 给滚回命令。
全程"改名保留",任何一步都能滚回。
用法: python3 auto_swap.py [新端目录=/opt/new_server] [线上目录=/opt/jiutian_new]
需 root 运行。"""
import re, os, sys, glob, time, shutil, subprocess

NEW = sys.argv[1] if len(sys.argv) > 1 else "/opt/new_server"
LIVE = sys.argv[2] if len(sys.argv) > 2 else "/opt/jiutian_new"
TS = time.strftime("%Y%m%d_%H%M%S")


def ask(q, default_no=True):
    tip = "[y/N]" if default_no else "[Y/n]"
    try:
        a = input("\n>>> %s %s " % (q, tip)).strip().lower()
    except EOFError:
        a = ""
    if not a:
        return not default_no
    return a in ("y", "yes", "是")


def die(msg):
    print("\n[X] " + msg)
    print("    停在这里了,没动你的线上服。截图发老板。")
    sys.exit(1)


print("=" * 42)
print(" FiveM 全自动换端  (线上:%s)" % LIVE)
print("=" * 42)

# ---------- 0. 基本检查 ----------
if not os.path.isdir(LIVE) or not os.path.isfile(os.path.join(LIVE, "server.cfg")):
    die("线上目录 %s 不对(没有 server.cfg)。" % LIVE)
if not os.path.isdir(NEW) or not os.listdir(NEW):
    die("新端目录 %s 不存在或是空的。先把新端上传/解压到这里。" % NEW)

old_cfg_text = open(os.path.join(LIVE, "server.cfg"), encoding="utf-8", errors="ignore").read()

# 解析连接串(用来备份数据库 + 可选导库)
m = re.search(r'mysql_connection_string\s+"([^"]+)"', old_cfg_text) or \
    re.search(r"mysql_connection_string\s+'([^']+)'", old_cfg_text)
conn = m.group(1) if m else None
db = None
if conn:
    mm = re.match(r'mysql://[^:]+:[^@]*@[^:/]+(?::\d+)?/([^?]+)', conn)
    if mm:
        db = mm.group(1)
    else:
        for part in conn.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k.strip().lower() == "database":
                    db = v.strip()

print("\n第1步: 请先在 txAdmin 网页里【停止服务器】(Stop)。")
if not ask("已经停服了吗?", default_no=False):
    die("先去 txAdmin 停服,再回来跑。")

# ---------- 1. 自动备份 ----------
print("\n第2步: 自动备份(服务端 + 数据库)...")
bak_tar = "/opt/jiutian_OLD_%s.tar.gz" % TS
r = subprocess.run(["tar", "czf", bak_tar, "-C", LIVE, "resources", "server.cfg"],
                   stderr=subprocess.PIPE)
if r.returncode != 0 or not (os.path.isfile(bak_tar) and os.path.getsize(bak_tar) > 0):
    die("服务端备份失败: " + r.stderr.decode("utf-8", "ignore")[:200])
print("   ✓ 服务端已备份 -> %s (%.1f MB)" % (bak_tar, os.path.getsize(bak_tar) / 1e6))

bak_sql = "/opt/db_backup_%s.sql" % TS
if db:
    # 用本机 root socket 免密导出,避开 TCP 的 root@localhost 报错
    with open(bak_sql, "wb") as f:
        r = subprocess.run(["mysqldump", "--default-character-set=utf8mb4", db],
                           stdout=f, stderr=subprocess.PIPE)
    if r.returncode != 0 or os.path.getsize(bak_sql) == 0:
        die("数据库备份失败: " + r.stderr.decode("utf-8", "ignore")[:200] +
            "\n    (如果是权限问题,可能 root socket 免密被改过)")
    print("   ✓ 数据库已备份 -> %s (%.1f MB)" % (bak_sql, os.path.getsize(bak_sql) / 1e6))
else:
    print("   [!] 没解析出数据库名,跳过数据库备份(继续)。")

# ---------- 2. 定位新端 resources ----------
print("\n第3步: 找新端的 resources ...")
cands = subprocess.run(["find", NEW, "-maxdepth", "3", "-type", "d", "-name", "resources"],
                       stdout=subprocess.PIPE).stdout.decode().split()
new_res = None
if cands:
    new_res = sorted(cands, key=len)[0]
else:
    # 新端本身可能就是 resources(里面直接是各资源文件夹)
    subs = [os.path.join(NEW, d) for d in os.listdir(NEW) if os.path.isdir(os.path.join(NEW, d))]
    if any(os.path.isfile(os.path.join(s, "fxmanifest.lua")) or s.strip("[]") != s for s in subs):
        new_res = NEW
if not new_res:
    die("在新端里找不到 resources 文件夹。可能没解压好或结构特殊。")
print("   ✓ 新端 resources: %s" % new_res)

# 新端自带的 cfg / sql
new_cfgs = subprocess.run(["find", NEW, "-maxdepth", "3", "-iname", "server.cfg"],
                          stdout=subprocess.PIPE).stdout.decode().split()
new_cfg = sorted(new_cfgs, key=len)[0] if new_cfgs else None
new_sqls = subprocess.run(["find", NEW, "-maxdepth", "3", "-iname", "*.sql"],
                          stdout=subprocess.PIPE).stdout.decode().split()
print("   新端自带 cfg: %s" % (new_cfg or "无"))
print("   新端自带 sql: %s" % (", ".join(new_sqls) if new_sqls else "无"))

# ---------- 3. 扫后门 ----------
print("\n第4步: 扫新端后门 ...")
hits = []
for root, _, files in os.walk(new_res):
    for fn in files:
        if not fn.lower().endswith((".lua", ".js", ".json", ".cfg")):
            continue
        p = os.path.join(root, fn)
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        low = t.lower()
        has_load = ("loadstring" in low) or re.search(r'\bload\s*\(', low)
        has_b64 = ("base64" in low) or bool(re.search(r'(\\x[0-9a-f]{2}){6,}', low))
        if has_load and has_b64:
            hits.append(("高危", os.path.relpath(p, new_res), "load + base64/\\x 一起出现"))
        if "discord.com/api/webhooks" in low or "discordapp.com/api/webhooks" in low:
            hits.append(("可疑", os.path.relpath(p, new_res), "Discord webhook 外传"))
        if re.search(r'os\.execute|io\.popen', low):
            hits.append(("可疑", os.path.relpath(p, new_res), "执行系统命令"))
severe = [h for h in hits if h[0] == "高危"]
if hits:
    print("   命中 %d 处:" % len(hits))
    for lv, f, why in hits[:15]:
        print("     [%s] %s — %s" % (lv, f, why))
    if severe:
        print("\n   ⚠️ 有【高危】(load+base64,典型后门特征)!")
        if not ask("确定这个端可信、还要继续换吗?", default_no=True):
            die("已放弃换这个端(明智)。你的线上服没动。")
else:
    print("   ✓ 没扫到明显后门特征。")

# ---------- 4. 换 resources ----------
print("\n第5步: 换 resources(旧的改名 resources_OLD 留着)...")
live_res = os.path.join(LIVE, "resources")
old_res_bak = os.path.join(LIVE, "resources_OLD")
if os.path.exists(old_res_bak):
    shutil.rmtree(old_res_bak)
if os.path.exists(live_res):
    os.rename(live_res, old_res_bak)
shutil.copytree(new_res, live_res)
subprocess.run(["chown", "-R", "www:www", live_res], stderr=subprocess.DEVNULL)
print("   ✓ 已换上新 resources(旧的在 resources_OLD)")

# ---------- 5. cfg 接线 ----------
print("\n第6步: 接线 server.cfg(把你这台的 license/数据库/端口搬过去)...")
shutil.copy(os.path.join(LIVE, "server.cfg"), os.path.join(LIVE, "server.cfg.OLD"))
KEYS = ["sv_licenseKey", "mysql_connection_string", "endpoint_add_tcp", "endpoint_add_udp"]
mine = {}
for k in KEYS:
    mm = re.search(r'^\s*(?:set[r]?\s+)?%s\s+.*$' % re.escape(k), old_cfg_text, re.M)
    if mm:
        mine[k] = mm.group(0).strip()

if new_cfg:
    # 成品端常把配置拆成多个 .cfg(server.cfg 里 exec server_plugin.cfg 等),
    # 把 server.cfg 同目录的其它 .cfg 一并搬过来,否则起服报缺文件。
    ncdir = os.path.dirname(new_cfg)
    moved = 0
    for fn in os.listdir(ncdir):
        if fn.lower().endswith(".cfg") and fn.lower() != "server.cfg":
            dst = os.path.join(LIVE, fn)
            if os.path.isfile(dst):
                shutil.copy(dst, dst + ".OLD")
            shutil.copy(os.path.join(ncdir, fn), dst)
            moved += 1
    if moved:
        subprocess.run("chown www:www %s/*.cfg" % LIVE, shell=True,
                       stderr=subprocess.DEVNULL)
        print("   ✓ 一并搬了 %d 个附属 cfg(server_plugin/target/inventory 等)" % moved)
    txt = open(new_cfg, encoding="utf-8", errors="ignore").read()
    for k, line in mine.items():
        pat = re.compile(r'^\s*(?:set[r]?\s+)?%s\s+.*$' % re.escape(k), re.M)
        if pat.search(txt):
            txt = pat.sub(line, txt, count=1)   # 用你的值替换新端的
        else:
            txt = line + "\n" + txt               # 新端没有就补上你的
    open(os.path.join(LIVE, "server.cfg"), "w", encoding="utf-8").write(txt)
    print("   ✓ 用新端 cfg + 你的 license/数据库/端口,已生成 server.cfg")
    print("     (旧 cfg 备份在 server.cfg.OLD)")
else:
    print("   [!] 新端没带 server.cfg,保留你原来的 cfg 不动。")
    print("     注意:新端资源的 ensure 行可能要按新端说明手动加(截图发老板)。")

# ---------- 6. 可选导库 ----------
print("\n第7步: 数据库")
if new_sqls and db:
    print("   新端自带数据库文件。导入 = 用新端的表结构,【老玩家数据会清空、重新开档】。")
    print("   想保留老玩家档就选 n(先不导,起服看看;报表错误再回来导)。")
    if ask("要导入新端数据库吗?(会清档)", default_no=True):
        sql = sorted(new_sqls, key=len)[0]
        # 修 MySQL8 专用排序规则,兼容 MariaDB
        try:
            data = open(sql, encoding="utf-8", errors="ignore").read()
            data = data.replace("utf8mb4_0900_ai_ci", "utf8mb4_general_ci")
            fixed = sql + ".fixed"
            open(fixed, "w", encoding="utf-8").write(data)
        except Exception:
            fixed = sql
        with open(fixed, "rb") as f:
            r = subprocess.run(["mysql", "--default-character-set=utf8mb4", db],
                               stdin=f, stderr=subprocess.PIPE)
        if r.returncode == 0:
            print("   ✓ 新端数据库已导入(老档已被覆盖)")
        else:
            print("   [X] 导入报错(不影响已换好的资源,可稍后处理):",
                  r.stderr.decode("utf-8", "ignore")[:200])
    else:
        print("   ✓ 跳过导库,保留老玩家数据。")
else:
    print("   新端没带 sql 或没数据库信息,跳过(用现有数据库)。")

# ---------- 完成 ----------
print("\n" + "=" * 42)
print(" ✅ 换端完成!现在去 txAdmin 点【启动 Start】")
print("    进游戏跑一圈:能进服、能出生、菜单/背包/车正常 = 成功")
print("=" * 42)
print("\n🔙 想滚回换之前?粘这条:")
print("   cd %s && rm -rf resources && mv resources_OLD resources && "
      "cp server.cfg.OLD server.cfg && chown -R www:www resources && "
      "echo 已还原" % LIVE)
if db and os.path.isfile(bak_sql):
    print("   数据库要还原老档再加: mysql %s < %s" % (db, bak_sql))
print("\n稳了几天没问题再删备份: rm -rf %s/resources_OLD %s/server.cfg.OLD" % (LIVE, LIVE))
