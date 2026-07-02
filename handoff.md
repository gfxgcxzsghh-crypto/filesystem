# 我的全部项目 · 交接文档(2026-07-02 更新版)

> ⚠️ **本文件含 API 密钥,只在你自己和 Claude 的对话里用,别发群/外传。**
> 担心泄露的话,可事后在各中转站后台重置 key。服务器/数据库密码请自己另外保管,本文档未写明文。

---

## 0. 服务器基础

- **公网 IP**:`111.170.11.156`
- 系统 Ubuntu,**root** 登录,**6 核 / 5.7G 内存**
- 我用**手机 Termius** 连服务器操作;**我也有电脑**(搞象棋桌面版/模组开发可以用)
- 服务器装有**宝塔面板**(可视化管理,账号/密码自己保管)
- 同机同时跑着 **FiveM 游戏服 + 一堆 AI 工具 + 象棋助手**,改任何东西注意别互相抢资源/抢端口

---

## 1. FiveM 游戏服(ESX Legacy + Overextended/ox 生态)

- **txAdmin** 管理面板
- 曾出过数据库故障(MySQL root 密码不匹配 → 全资源变红),已修复
  - 教训:改 `mysql_connection_string` 这类 **convar 必须完整重启 txAdmin** 才生效(`restart oxmysql` 没用)
- **安全红线**:FiveM 调 AI 的 key 在 `server.cfg` 用 `set`,**绝不能用 `setr`**(setr 会把密钥暴露给所有客户端)
- **已装的自制资源**:
  - `jt_repairbot` —— 自动维修
  - `jt_fun` —— 欢乐包:`/tpm` 传送标记点、`/firework` 烟花、`/superjump` 超级跳、`/dice` 骰子、`/coinflip` 抛硬币(结果全服广播)
- **原则**:拒绝任何盗版/破解 FiveM 资源(后门风险高)
- **待办**:管理员反应 919 面板功能无法使用(还没排查)

---

## 2. Claude Code 配置(已接 lk888 的真 · opus-4-8)

配置写在 `~/.claude/settings.json` 的 `env` 字段:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.lk888.ai",
    "ANTHROPIC_AUTH_TOKEN": "sk-31e37d97cec9473cc670eab9153ce6b34e8afe4d66eba48c",
    "ANTHROPIC_MODEL": "claude-opus-4-8",
    "ANTHROPIC_SMALL_FAST_MODEL": "claude-opus-4-8"
  }
}
```

- 这个 lk888 key **只开通了 `claude-opus-4-8` 一个模型**,其他模型会 403
- 改完要**完全退出 Claude Code 再重开**才生效;进去用 `/status` 看模型
- ⚠️ **官方订阅号(Claude Pro)在这台服务器上登不了**(2026-07-02 实测):`/login` 一律 OAuth 403,原因是**大陆服务器 IP 被 Anthropic 地区封锁**,清配置/清环境变量都没用,**别再试了**。订阅号要用只能在自己电脑上(网络环境能直连 Anthropic 的地方)装 Claude Code 登。
- 有备份:`~/.claude/settings.json.bak`

---

## 3. AI API 号 / 中转站(测号结论)

### lk888 —— 最强 Claude,稳(主力,写代码/改bug用这个)
- 地址:`https://api.lk888.ai`(管理页 g8kt.com,即「灵刻 AI」)
- key:`sk-31e37d97cec9473cc670eab9153ce6b34e8afe4d66eba48c`
- 有真 **claude-opus-4-8**(最新最强 Claude),只开了这一个模型(2026-07-02 复测存活 ✅)
- Anthropic 格式 `/v1/messages` + `x-api-key`;也兼容 OpenAI `/v1/chat/completions` + Bearer

### 清风站 —— 国产模型专用站,免费主力(2026-07-02 新增实测)
- 地址:`https://api.iamhc.cn/v1`
- key:`sk-yofQPPHAUONqR8Rge4rAk6PqQAd0ngd6mxxTrVmgZCZZO2uQ`
- **没有 Claude/GPT/Gemini**,25 个全是国产模型
- ✅ 实测能用:`DeepSeek-V4-Pro`(最强推荐)、`DeepSeek-V4-Flash`、`Kimi-K2.6`、`MiniMax-M2.7`、`Qwen3.5-397B-A17B`、`Qwen3.6-35B-A3B`、`Qwen3-Coder-Next-FP8`(代码)、`glm-4.7`、`kat-coder-pro-v2`(代码)、`step-3.5/3.7-flash`、`Spark-X2-Flash`
- ❌ 不能用:`glm-5.1`/`glm-5.2`(2026-07-02 EOL 下线)、`MiniMax-M3`(400)、`sensenova-u1-fast`(404)
- **同时支持 OpenAI 和 Anthropic(`/v1/messages`)两种格式**,能直接接 Claude Code

### supxh —— 稳,真 Claude/Gemini
- 地址:`https://api.supxh.xin/v1`
- 模型:`claude-opus-4-5`、`gemini-3.1-pro`
- keys:
  - `sk-HeyUwSzv2ZSbBQVon4Zc76vNAna5jridWGGPcG5H26ObIo9y`
  - `sk-K1L37fklieQjeWwIstem1A3PSqR3A2HQp2qcpNqZSyDyG23k`
  - `sk-So6WD2Wx9UjBKCOauqkvFLm94aYiL5fecXVXw2tj2aId6nZw`

### omale / o站 —— 不稳,常整站抽风,免费白嫖用(2026-07-02 复测)
- 地址:`https://omaleai.qzz.io/v1`
- ⚠️ 站经常报 503 `system memory overloaded`(整站内存爆),等会儿再试
- ⚠️ **模型名变了**:是 `deepseekv3.1`/`deepseekv3.2`(**没有中划线**);`gpt-5.4` 已下线,现在是 `gpt-5.5`/`gpt-5.3-high`
- 三个号:
  - **免费分组** `sk-N8oBAbazRw7PchgttrbGl4hVP2dXyTrwzWTUAhzJeu6gPgAh` → ✅ `gpt-4o`、`deepseekv3.2`、`deepseekv4-pro` 实测能用;`glm-5.1` 402 欠费
  - **pro 分组** `sk-GM5VJpzWY4xo218kFq5FbFAUkz5JLmt9pxbo5PjgMYs1NCaN` → **只剩 $0.0265**,claude 报余额不足,基本废了
  - **尾 Ga9** `sk-fbMqxFgVdVCoPd0ezCrOft8PAWsbnbBsF1QAgxN36h6wMGa9` → 复测时整站抽风没测出来,按之前记录只剩免费模型
- 规律:402/403=余额不足或模型没开;502/503=整站抽风(等会儿好)

### 其它
- **多 key 轮转网关**:`/opt/ai_gateway.py`(配置 `/opt/ai_pool.json`),监听 `127.0.0.1:8787`(仅本机),一个号挂了自动切下一个,Anthropic↔OpenAI 双向翻译
  - **当前号池(8 个,2026-07-02)**:supxh4/5/6(opus-4-5)→ qingfeng-ds4pro(DeepSeek-V4-Pro)→ omale-sonnet46 → omale-glm51 → omale-nemotron → zhipu兜底(glm-4.5-flash)
  - 备份:`/opt/ai_pool.json.bak`
  - 改号池后重启:`pkill -f ai_gateway.py; sleep 1; cd /opt && nohup python3 -u /opt/ai_gateway.py >/opt/ai_gateway.log 2>&1 &`
- **SillyTavern(云酒馆)**:`/opt/sillytavern`,端口 `8055`

### 模型怎么选(结论)
- **写代码/改 bug 最强**:lk888 `claude-opus-4-8`(Claude Code 就用它)
- **免费最强**:清风站 `DeepSeek-V4-Pro`
- **FiveM 游戏内 NPC 对话(轻量高频)**:清风站 `DeepSeek-V4-Flash` 或 o站号1 `gpt-4o`

---

## 4. 象棋皮卡鱼助手

- **引擎**:Pikafish **2026-01-02**(当前最新正式版,Elo ~3954,天梯第一),装在 `/opt/xq/pikafish` + `/opt/xq/pikafish.nnue`
- **网页服务**:`/opt/xq/server.py`(纯 Python stdlib),端口 `8090`,访问 `http://111.170.11.156:8090`
  - 前端 canvas 棋盘,后端调皮卡鱼 UCI,已接 **chessdb 云库**(`http://www.chessdb.cn`)、5 线程、1G 哈希
- **启动**:`cd /opt/xq && nohup python3 -u server.py >server.log 2>&1 &`
- **重启**(换文件后):`pkill -9 -f server.py` 后再跑上面启动命令
- **源码备份**:GitHub 仓库 `gfxgcxzsghh-crypto/filesystem`,分支 `claude/pensive-brown-vnw1nn`,文件 `xq_server.py`
  - 下载:`curl -L -o /opt/xq/server.py "https://raw.githubusercontent.com/gfxgcxzsghh-crypto/filesystem/claude/pensive-brown-vnw1nn/xq_server.py"`
- **坐标逻辑(已验证正确)**:开局生成标准 FEN `rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1`;`w`=红方走;前端 `uci2rc` 里 `棋盘行 = 9 - UCI行`
- **用法**:把局面摆得和实战一样 → 选「轮到谁走」→ 点「分析最优」看绿箭头 → 游戏里照走;「走最优」=网页同步自己这步;对手走后手动在网页摆上对手的子

### 背景(为啥搞象棋)
要用这个对付一个**加好友约战的「软件大佬」**——他用 **皮卡鱼 + 屠龙库 + 强机库**(软件流顶配)。所以我也要顶配。是**双方都用软件的约战**(不是坑随机真人,合规)。先拿天天「特级大师」试水。

### 待解决 / 下一步
1. 反馈「照网页提示走,打不过天天象棋特级大师」(特级大师 ≈ 人类特级大师/神1)。皮卡鱼 Elo 3954 理论上碾压。
2. 怀疑原因:**①云库优先在中局拖后腿**(已写改进:中局让皮卡鱼深算 8 秒、残局 ≤12 子才用云库,改进命令**可能还没跑**);**②手动同步局面易摆错**。
3. **我有电脑**。可能更优方案:**电脑桌面方案**(象棋桥 / 鹏飞象棋 / 兵河 + 皮卡鱼 + 云库),界面成熟、无同步 bug,跟对手同款配置。

---

## 5. 我的世界模组(已转国际版)

- 我玩**网易手机版**,但网易**锁死自制模组导入**(.mcaddon/.mcpack 导进去无反应)——网易策略,绕不过
- 已在 **iPhone 装了国际版基岩版**(App Store 外区 Apple ID 付费下的**正版**),国际版双击 `.mcaddon` 秒导入
- Claude 做过:**灭世神剑 v3**(`.mcaddon`,一刀 32767 伤害 + 永久发光),适配 1.21+(`format_version` 1.21.0、icon 用 `{"textures":{"default":...}}`)。文件直接发我的,**没传 GitHub**
- 想要**可骑乘机甲**(坐进去开):做过 v2 方块人形机甲(500血/能骑能开),**我嫌丑,造型要重做**(我审美要求高,最好我给参考图照着做)
- 复杂模组(机甲变身/技能/特效)要**电脑 + 网易 MCStudio(Python ModSDK)** 或国际版 ScriptAPI,手机做不了纯 JSON
- 基岩版自定义物品 1.21+ 要点:`format_version` 1.21.0;icon 对象格式;伤害 `minecraft:damage`;`foil` 发光新版可能不吃 → 拿到后 `/enchant` 附魔保底发光

---

## 我的偏好(给 Claude)
- 始终用**简体中文**回复,说人话/笨蛋话
- 给**能直接复制粘贴**的命令(我用手机 Termius)
- 注意省钱:别随便测付费号、别让长对话无意义堆积

---

## 给接手 Claude 的话(前任 Claude 的经验,认真看)

- **用户是手机党**(iPhone + Termius 连服务器)。给命令务必**能一次性复制粘贴**,别太长、别带会被手机/bash 搞坏的字符。
- **省钱第一**:用户多次强调 Claude 贵、付费 API 号贵。**别随便测付费号**(测前先问)、别让对话无意义堆长、能用服务器本地免费方案就别烧 token。
- **风格**:简体中文 + 笨蛋话 + 直接给结果。少废话、**少甩锅给用户**(用户很反感"是你的问题")。
- **区分两个界面**:黑框 bash(`root@...#`)敲 `claude`/`ls` 这类命令;`/login` `/status` `/model` 这些**斜杠命令只能在 Claude Code 界面里**敲,在 bash 里敲会报 No such file。
- **订阅号登录 403 已定性**:是大陆 IP 被 Anthropic 封,不是配置问题,别再带用户折腾这个。
- **传文件到服务器的坑(都踩过)**:
  - Bash 直接 curl 上传文件托管 / 调 GitHub API 写 → **会被权限拦**
  - 环境里的 `GITHUB_TOKEN` 是**只读**的(`git push` 认证失败)
  - ✅ 可行路径:用 `mcp__github__create_or_update_file` 把文件写到仓库 `gfxgcxzsghh-crypto/filesystem`(分支用当次会话指定的 claude/xxx 分支),用户再 `curl` 下载
  - 服务器下 GitHub **大文件慢** → 用镜像 `https://ghfast.top/<github原始url>`;小文件直连 raw 也快
  - 改服务器上已有的小文件 → **用 python replace 改那几行**,别重传整个文件(省事省钱)
  - **别手打 base64**(手打崩过导致 invalid input);别让 XML 标签漏进命令;命令里带 `!` 会触发 bash history expansion 报错
- **测中转站的套路**(照抄就行):先 `GET /models` 拉列表(模型名经常跟记录对不上,别信旧文档直接测),再对每个模型发一条 `max_tokens≤10` 的"回复ok"实测;402=欠费、403=没开/余额、404=模型没了、503=整站抽风。
- **象棋坐标已反复验证正确**(开局生成标准 FEN),除非有确凿 bug,别乱动坐标逻辑
- 用户折腾久了会**不耐烦** → 优先给**一步到位、确定能成**的方案,别来回试

---

## 我接下来想干
〔在这里写你的需求,例如:象棋改电脑桌面版 / 继续搞 FiveM(919面板问题) / MC 机甲重做 / 别的〕
