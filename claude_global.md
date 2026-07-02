# 主人的使用偏好(Claude 每次必读)

- 用**简体中文**回复,说人话/笨蛋话,别端着。
- 给命令务必**能一次性复制粘贴**(主人用手机 Termius),别太长、别带会被手机/bash 搞坏的字符(`!`、裸 XML 标签、手打 base64 都禁)。**长内容别用 heredoc 直接粘(手机会截断),改用 curl 从 GitHub 下载。**
- **省钱第一**:别乱测付费 API 号(测前先问),别让对话无意义堆长,能用本地免费方案就别烧 token。
- **少甩锅**:别说"是你的问题",主人很反感。出错先自己查。
- 优先给**一步到位、确定能成**的方案,别来回试。主人折腾久了会不耐烦。
- 区分界面:黑框 bash 敲 `claude`/`ls`;`/login` `/status` `/model` 这些斜杠命令**只能在 Claude Code 界面里**敲。

# 项目速查(详情看 /root/handoff.md)

- **服务器**:111.170.11.156,Ubuntu 6核5.7G,root,宝塔面板。同机跑 FiveM + AI工具 + 象棋,改东西别抢端口。
- **FiveM 服**:ESX Legacy + ox 生态,txAdmin 管理,装在 /opt/jiutian_new,cfg 在 /opt/jiutian_new/server.cfg。红线:AI key 用 `set` 不能用 `setr`。
- **象棋助手**:Pikafish 引擎,网页 /opt/xq/server.py 端口 8090。源码备份在 GitHub filesystem 仓库。
- **AI 中转站**:lk888(最强 opus-4-8,主力)、清风站(免费 DeepSeek-V4-Pro)、supxh、o站。轮转网关 /opt/ai_gateway.py 端口 8787,号池 /opt/ai_pool.json。
- **MC 模组**:iPhone 国际版基岩版,做 .mcaddon。主人审美高,造型要给参考图。
- **订阅号登录**:大陆服务器 IP 被 Anthropic 封,登不了,别再试。

# 开工第一件事
若 /root/handoff.md 存在,先读它了解全局,再干活。
